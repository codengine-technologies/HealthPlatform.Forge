# meta-task-046-s3776-campaign-tracker.md — Campagne S3776 cognitive complexity (39 méthodes)

> ⚠️ **Préfixe `meta-`** délibéré : ce fichier n'est PAS un `todo-task-*.md`
> et n'est PAS pické par `/forge`. Il sert de **tracker** pour la campagne
> S3776 que l'humain pilote manuellement via `/sonar-s3776 api-mail`,
> 1 méthode = 1 task = 1 PR.

**Repos**: api-mail
**Epic**: E010

## Objectif

Éliminer les **39 occurrences** de `csharpsquid:S3776` (Cognitive Complexity
of methods should not be too high) sur `api-mail`. Règle maison :
1 méthode = 1 PR via `/sonar-s3776 api-mail` (voir
`.claude/commands/sonar-s3776.md`).

Chaque run `/sonar-s3776 api-mail` crée à la volée son propre
`todo-sonar-s3776-{slug}-{YYYYMMDD}.md`, sa branche `chore/sonar-s3776-{slug}-{YYYYMMDD}`,
et sa PR. Les tasks générées **doivent** déclarer `**Epic**: E010` pour être
attachées à l'EPIC par `/tech-writer`.

## Pourquoi pas une todo-task standard

- `/forge` traiterait `todo-task-046-*.md` comme une US à `/start` →
  `/develop`, ce qui n'a pas de sens (pas de "code à développer", c'est
  un workflow itératif manuel piloté par `/sonar-s3776`)
- 39 PRs distinctes = 39 cycles HAG indépendants, à étaler dans le temps
  selon l'arbitrage humain et la disponibilité de test coverage

## Liste des 39 méthodes à traiter (Sonar snapshot 2026-05-17)

Triée par complexité **décroissante** (top offenders en premier) — ordre
recommandé pour la campagne car les méthodes les plus complexes apportent
le plus de valeur Sonar par PR.

| # | Complexité | Fichier | Ligne | Done ? |
|---|---|---|---|---|
| 1 | **80** | `src/Infrastructure/Repository/MailRepository.cs` | 666 | ☐ |
| 2 | **75** | `src/Application/Services/Implementation/ImapService.cs` | 753 | ☐ |
| 3 | 45 | `src/Application/Services/Implementation/SemanticSearchService.cs` | 638 | ☐ |
| 4 | 41 | `src/Infrastructure/Repository/SemanticSearchRepository.cs` | 518 | ☐ |
| 5 | 41 | `src/Infrastructure/Repository/MailRepository.cs` | 39 | ☐ |
| 6 | 41 | `src/Application/Services/Implementation/MarkdownPdfRenderer.cs` | 339 | ☐ |
| 7 | 41 | `src/Application/Services/Implementation/ImapService.cs` | 474 | ☐ |
| 8 | 36 | `src/Infrastructure/Repository/AuditTraceRepository.cs` | 34 | ☐ |
| 9 | 33 | `src/Application/Services/Implementation/ImapService.cs` | 1392 | ☐ |
| 10 | 31 | `src/Api/Middleware/UserContextEnricherMiddleware.cs` | 35 | ☐ |
| 11 | 29 | `src/Application/Services/Implementation/BackgroundImapService.cs` | 143 | ☐ |
| 12 | 26 | `src/Application/Services/Implementation/OcspValidationService.cs` | 176 | ☐ |
| 13 | 26 | `src/Application/Services/Implementation/AiConversationService.cs` | 247 | ☐ |
| 14 | 24 | `src/Application/Models/MailDigest.cs` | 118 | ☐ |
| 15 | 23 | `src/Infrastructure/Repository/MailRepository.cs` | 248 | ☐ |
| 16 | 23 | `src/Infrastructure/Repository/MailRepository.cs` | 1806 | ☐ |
| 17 | 23 | `src/Application/Services/Implementation/TextChunkingService.cs` | 166 | ☐ |
| 18 | 23 | `src/Application/Services/Implementation/AnnuaireSante/Parsers/FhirBundleParser.cs` | 57 | ☐ |
| 19 | 21 | `src/Application/Services/Implementation/SemanticSearchService.cs` | 29 | ☐ |
| 20 | 19 | `src/Application/Services/Implementation/ImapConnectionService.cs` | 118 | ☐ |
| 21 | 19 | `src/Application/Services/Implementation/CrlValidationService.cs` | 178 | ☐ |
| 22 | 19 | `src/Api/Helpers/RequestHelper.cs` | 26 | ☐ |
| 23 | 18 | `src/Infrastructure/Repository/MailRepository.cs` | 402 | ☐ |
| 24 | 18 | `src/Application/Services/Implementation/PendingActionService.cs` | 73 | ☐ |
| 25 | 18 | `src/Application/Services/Implementation/ImapService.cs` | 78 | ☐ |
| 26 | 17 | `src/Infrastructure/Repository/MailRepository.cs` | 1589 | ☐ |
| 27 | 17 | `src/Application/Services/Implementation/BackgroundImapService.cs` | 284 | ☐ |
| 28 | 16 | `src/Infrastructure/Repository/PatientRepository.cs` | 565 | ☐ |
| 29 | 16 | `src/Infrastructure/Repository/MailRepository.cs` | 2010 | ☐ |
| 30 | 16 | `src/Application/Services/Implementation/TextChunkingService.cs` | 408 | ☐ |
| 31 | 16 | `src/Application/Services/Implementation/OnlineMailDataProvider.cs` | 52 | ☐ |
| 32 | 16 | `src/Application/Services/Implementation/MarkdownPdfRenderer.cs` | 206 | ☐ |
| 33 | 16 | `src/Application/Services/Implementation/ImapService.cs` | 938 | ☐ |
| 34 | 16 | `src/Application/Services/Implementation/CdaParsingService.cs` | 357 | ☐ |
| 35 | 16 | `src/Application/Services/Implementation/BackgroundImapService.cs` | 446 | ☐ |
| 36 | 16 | `src/Application/Services/Implementation/AnnuaireSante/Strategies/SpecialtySearchStrategy.cs` | 45 | ☐ |
| 37 | 16 | `src/Application/Services/Implementation/AnnuaireSante/Strategies/NameSearchStrategy.cs` | 79 | ☐ |
| 38 | 16 | `src/Application/Services/Implementation/AnnuaireSante/Strategies/CombinedSearchStrategy.cs` | 332 | ☐ |
| 39 | 16 | `src/Api/Controllers/V1/MailController.cs` | 1166 | ☐ |

Limite Sonar : **15**. Toutes les méthodes ci-dessus sont **au-dessus**.

## Concentration par fichier (top hotspots)

| Fichier | # méthodes S3776 |
|---|---|
| `Infrastructure/Repository/MailRepository.cs` | **7** |
| `Application/Services/Implementation/ImapService.cs` | **5** |
| `Application/Services/Implementation/BackgroundImapService.cs` | 3 |
| `Application/Services/Implementation/MarkdownPdfRenderer.cs` | 2 |
| `Application/Services/Implementation/SemanticSearchService.cs` | 2 |
| `Application/Services/Implementation/TextChunkingService.cs` | 2 |
| 18 autres fichiers | 1 chacun |

## Procédure par PR

Pour chaque méthode (idéalement dans l'ordre décroissant de complexité) :

```
/sonar-s3776 api-mail
```

La commande :
1. Détecte la prochaine méthode S3776 la plus complexe (peut être pilotée
   par l'issue key explicite si besoin de réordonner)
2. Vérifie la coverage existante de la méthode ; sinon écrit des tests de
   caractérisation **en amont** (commit `test(sonar-s3776): ...`)
3. Crée `tasks/todo-sonar-s3776-{slug}-{YYYYMMDD}.md` avec
   `**Epic**: E010` (à vérifier — voir "Action requise" ci-dessous)
4. Crée la branche `chore/sonar-s3776-{slug}-{YYYYMMDD}` sur `api-mail`
5. Refactor (Extract Method / guard clauses / Strategy / etc.)
6. Build + tests verts
7. Re-analyse Sonar, vérifie disparition de l'issue
8. `/review` → PR → label `awaiting-human-merge` → humain merge

## Action requise sur `/sonar-s3776`

Le template de task dans `.claude/commands/sonar-s3776.md` **ne déclare
pas `**Epic**: E010`** aujourd'hui. Sans ce champ, les 39 tasks générées
ne seront pas attachées à l'EPIC E010 par `/tech-writer`.

Deux options :

- **A — Patch ponctuel** : à chaque fois qu'une task S3776 est créée par
  `/sonar-s3776 api-mail`, ajouter manuellement la ligne `**Epic**: E010`
  dans le todo généré avant le `/start`. Acceptable pour quelques PRs,
  pénible pour 39.
- **B — Patch durable (recommandé)** : modifier le template dans
  `.claude/commands/sonar-s3776.md` pour ajouter `**Epic**: E010` (ou
  rendre l'EPIC paramétrable). À faire en première PR de la campagne si
  l'humain veut le tracking auto.

## Suivi

- Cocher chaque méthode de la table ci-dessus au fur et à mesure des merges
- Vérifier sur Sonar : compteur S3776 décroissant
- Quand `S3776 == 0` → fermer cet EPIC

## Liens

- Règle Sonar : https://rules.sonarsource.com/csharp/RSPEC-3776
- Spec `/sonar-s3776` : `.claude/commands/sonar-s3776.md`
- Blacklist `/sonar` (pourquoi S3776 est hors batch) : `agents/sonar-blacklist.yml`
