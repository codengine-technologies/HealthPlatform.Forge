# todo-task-033.md — Cleanup Sonar massif api-mail (20 itérations, 1 PR sans limite de fichiers)

**Repos**: api-mail
**Dependencies**: done-task-032
**Epic**: E009

## Objectif

Faire chuter de manière significative la dette SonarQube du backend
`api-mail` en exécutant un **cycle de cleanup automatisé sur 20 itérations
de sécurité**. Toutes les catégories d'issues Sonar sont traitées **à
l'exception de S3776 (cognitive complexity, réservé à `/sonar-s3776`)**, en
restant strictement dans le critère "**pas de risque de régression**" validé
par la suite de tests étendue à task-032.

US purement **technique / dette** — aucun nouveau comportement métier.
Rattachée à E009 via la section "KPIs Sonar & Qualité" maintenue par
`/tech-writer`.

## Pré-requis (bloquants)

- `done-task-032` mergée — couverture ≥ 80 % line / 70 % branch.
- La suite de tests étendue **est** l'oracle de non-régression : tout
  refactor qui passe `dotnet build` + `dotnet test` est sûr ; tout refactor
  qui casse ≥ 1 test est rollback **automatique** avant commit.

## Périmètre Sonar — toutes catégories sauf S3776

**Inclus** :
- **Code smells safe** — unused imports, naming, `var` vs explicit, boolean
  simplification, redundant null check, `using` statement, `is` patterns, …
- **Code smells tactiques** — extraction de constante, renommage paramètre,
  inversion condition triviale, conversion `if/else` → ternaire / switch
  expression.
- **Bugs** — uniquement si la correction reste **mécanique** (suggestion
  Roslyn / Sonar acceptable telle quelle) : NRE potentielle protégée,
  `IDisposable` non disposé encapsulé en `using`, `await` manquant, etc.
- **Vulnerabilities** & **Security Hotspots** — idem, mécanique uniquement.

**Exclu explicitement** :
- **S3776 (cognitive complexity)** — réservé à `/sonar-s3776` (1 méthode =
  1 PR avec characterization tests). Aucune méthode S3776 n'est touchée
  ici, même si l'IDE le suggère.

## Critère "pas de risque de régression"

Pour chaque issue candidate, le pipeline applique cette logique :

- ✅ **Prendre** si :
  - Le fix est un rewrite **syntaxique mécanique** (suggestion automatique
    Sonar / Roslyn appliquable telle quelle)
  - **Et** `dotnet build` reste vert après le fix
  - **Et** `dotnet test` reste vert après le fix
- ❌ **Skipper** (et noter dans la liste des skips) si :
  - Le fix change un comportement runtime observable (catch swallow → throw,
    default value change, ordre d'évaluation, type d'exception levée…)
  - Le fix demande une décision métier (e.g. "log et continuer" vs
    "throw et propager")
  - Le fix casse ≥ 1 test → **rollback systématique du fichier**, issue
    listée comme skip avec mention "test failure"

Toute issue skippée est tracée : `Sxxxx | Fichier:Ligne | Raison`.

## Boucle d'exécution — 20 itérations max

À chaque itération :

1. `dotnet sonarscanner begin /k:"…" /d:sonar.host.url=… /d:sonar.token=…`
2. `dotnet build HealthPlatform.Api.Mail.sln`
3. `dotnet test HealthPlatform.Api.Mail.sln`
4. `dotnet sonarscanner end /d:sonar.token=…`
5. Récupérer la liste d'issues actuelles (API SonarQube), filtrer les
   catégories incluses, **exclure S3776**.
6. Trier par "facilité de fix" (préférer single-line / single-file).
7. Pour les ~30 issues les plus simples de l'itération :
   - Appliquer le fix (Edit ciblé, surface minimale)
   - `dotnet build` → si rouge, **rollback ce fichier**
   - `dotnet test` → si rouge, **rollback ce fichier** (issue → skip)
8. Commit `chore(sonar): iteration N — Δ issues` sur la branche en cours.

**Critères d'arrêt** (premier vrai gagne) :

- 20 itérations atteintes
- Plus aucune issue safe candidate (delta zero deux itérations consécutives)
- Erreur de tooling Sonar (réseau, token, scanner KO) → écrire
  `questions/task-033.md` et stopper sans pousser de PR partielle

## Definition of Done

- [ ] Build passe (0 erreur)
- [ ] Tests passent (0 failure) — **comptage identique** à celui de la fin de task-032
- [ ] Au moins **50 issues Sonar** corrigées au total (seuil "progression significative")
- [ ] Aucun fichier de production avec changement de comportement runtime
      (vérifié par : tests inchangés et toujours verts ; revue manuelle par
      `/review` des diffs touchant `catch` / `throw` / `return` / contrôles d'accès)
- [ ] Aucune modification touchant S3776 (cognitive complexity)
- [ ] Couverture line / branch après cleanup ≥ seuils task-032 (80 % / 70 %)
- [ ] Body de PR contient le bloc KPIs (cf. ci-dessous)
- [ ] Body de PR contient la liste des issues skippées avec raison

## KPIs (à publier dans le body de PR — repris par `/tech-writer` pour E009)

```
### Cleanup Sonar api-mail — task-033

| Catégorie               | Issues avant | Issues après | Δ      |
|-------------------------|--------------|--------------|--------|
| Code smells (hors S3776)|     XXXX     |     XXXX     |  -XXXX |
| Bugs                    |       XX     |       XX     |    -XX |
| Vulnerabilities         |       XX     |       XX     |    -XX |
| Security hotspots       |       XX     |       XX     |    -XX |
| **Total (hors S3776)**  |     XXXX     |     XXXX     |  -XXXX |

- Itérations effectuées : NN / 20
- Critère d'arrêt : (20 atteintes | plus de candidats | tooling KO)
- Fichiers touchés : NN
- LOC modifiées (+ / -) : +XXX / -XXX
- Issues skippées (risque régression) : NN — détail dans la section dédiée
- Couverture line / branch après cleanup : XX % / XX % (≥ task-032)
- Durée totale de la boucle : NNm
```

### Issues skippées (à reproduire dans le body PR)

```
Sxxxx | path/to/File.cs:LL | Raison du skip (1 ligne)
...
```

## Manual Test Plan

1. `cd Api/Mail`
2. `dotnet build HealthPlatform.Api.Mail.sln` → 0 erreur
3. `dotnet test HealthPlatform.Api.Mail.sln` → 0 failure, **même comptage**
   que task-032
4. Comparer le rapport SonarQube avant / après (UI projet) — vérifier la
   chute des compteurs Code smells / Bugs / Vulnerabilities / Security
   hotspots conforme aux KPIs annoncés.
5. Smoke run end-to-end :
   - `dotnet run --project src/mss.mail.api`
   - `GET /api/health` → 200
   - `GET /api/mails` (liste basique) → 200
   - 1 endpoint POST métier représentatif (au choix selon ce qui est
     facilement testable manuellement) → comportement attendu identique
     à avant la PR.

## Notes

- PR potentiellement **très volumineuse** (>> 30 fichiers). Le plafond
  habituel de la règle 5 est explicitement **levé** ici par décision PO
  validée à la rédaction (cleanup mécanique, review accélérée par la
  nature répétitive des diffs).
- En cas de tooling Sonar non disponible localement / CI cassée pendant la
  boucle, écrire `questions/task-033.md` et stopper la chaîne — ne pas
  improviser un fallback partiel.
- US-sœur **`task-032`** doit être mergée avant. Si `/start task-033` est
  invoqué alors que `task-032` n'est pas `done-`, refuser et demander à
  l'humain de finir task-032 d'abord.
