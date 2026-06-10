# todo-task-067-test-coverage-raise.md — Campagne itérative de couverture de tests (code-coverage-skill)

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Type**: chore (→ `/start` utilise le préfixe `chore/`)

## Objective

Augmenter **massivement** la couverture de tests unitaires et d'intégration du
backend `api-mail`, en exécutant le processus itératif défini par le skill
[.claude/skills/code-coverage-skill/SKILL.md](.claude/skills/code-coverage-skill/SKILL.md) :

```
analyse SonarQube → classes < 98% de couverture → création des tests
manquants → validation → re-analyse → itération suivante
```

- **Couverture de départ** : 77.4% (mesure SonarQube du 2026-06-10, projet `healthplatform`).
- **Condition d'arrêt** (celle atteinte en premier) : couverture globale **≥ 95%**
  (cible `agents/sonar-targets.yml` ; le 98% du skill reste l'ambition) **OU
  5 itérations** complètes.
- **Sélection par itération** : 1 à 10 classes, priorisées par impact
  (`uncovered_lines` décroissant), couches dans l'ordre Domain → Application →
  Infrastructure → Api, en évitant les classes exigeant des mocks HTTP
  complexes quand des classes plus simples restent disponibles.

### Cadrage des conventions (décision PO)

Le skill mentionne Moq + FluentAssertions ; **le repo utilise xUnit +
NSubstitute + `Assert` natif** (règle 1 CLAUDE.md, base de tests existante,
versions centralisées sans Moq ni FluentAssertions). La task suit le skill
pour le **processus itératif** et les **conventions du repo** pour l'écriture
des tests :

- xUnit (`[Fact]` / `[Theory]`), Arrange / Act / Assert, un comportement par test
- NSubstitute pour les collaborateurs externes
- Nommage descriptif `Method_Context_ExpectedResult` (convention dominante du repo)
- Mapping source → projet de test : `src/Domain` → `mss.mail.domain.tests`,
  `src/Application` → `mss.mail.application.tests`, `src/Infrastructure` →
  `mss.mail.infrastructure.tests`, `src/Api` → `mss.mail.api.tests`
  (+ `mss.mail.integration.tests` pour les parcours bout-en-bout
  Testcontainers déjà outillés)

### Garde-fous (non négociables)

1. **Aucune modification du code de production** — seuls les fichiers de test
   sont créés/modifiés. Exception unique tolérée : un `InternalsVisibleTo` ou
   un hook interne de test *si indispensable*, justifié dans le journal.
2. Les attributs `[ExcludeFromCodeCoverage]` existants **ne sont pas retirés**
   dans cette task — leur levée est une décision au cas par cas (précédent
   task-032 / Option A4) qui passe par une US dédiée.
3. **Aucun test trivial** (sans assertion, ou n'exerçant aucune branche) —
   chaque test couvre un comportement nominal, limite ou d'erreur réel.
4. **Aucune donnée de santé réelle dans les fixtures** : INS/NIR factices,
   emails de test, contenus CDA issus des samples anonymisés existants
   (`Resources/cda-samples/`).
5. Les 3 tests rouges pré-existants documentés (middleware DB-name Release,
   IMAP cancel flaky, MailExport PDF flaky) ne comptent pas comme régression
   — mais aucun nouveau test flaky n'est accepté.

## Gherkin

_Pas de `.feature` (BDD déprécié, cf. CLAUDE.md règle 1). US purement
outillage qualité — la valeur est mesurée par les métriques SonarQube._

## Definition of Done

- [ ] Build passes (`dotnet build HealthPlatform.Api.Mail.sln`, 0 erreurs)
- [ ] Tests pass (`dotnet test HealthPlatform.Api.Mail.sln`, 0 échecs hors
      les 3 rouges pré-existants documentés)
- [ ] Processus du skill exécuté : **au moins 1 et au plus 5 itérations**
      complètes (analyse → sélection → tests → validation → re-analyse),
      arrêt anticipé si couverture globale ≥ 95%
- [ ] **Couverture globale finale ≥ 83%** (plancher binaire : ≥ +5 points vs
      les 77.4% de départ) — l'ambition reste 95-98%, le plancher garantit
      un progrès substantiel sans bloquer la chaîne sur un objectif
      inatteignable en 5 itérations
- [ ] Journal d'itérations rempli dans la task (tableau : itération,
      couverture avant, classes traitées, tests ajoutés, couverture après)
- [ ] Aucun fichier de `src/` modifié (vérifiable :
      `git diff --name-only origin/develop...HEAD -- 'Api/Mail/src/'` vide,
      hors exception justifiée du garde-fou 1)
- [ ] Aucun attribut `[ExcludeFromCodeCoverage]` retiré
- [ ] Chaque nouveau test respecte les conventions repo (xUnit + NSubstitute,
      AAA, nommage descriptif, pas de test sans assertion)
- [ ] Quality Gate Sonar : 0 nouvelle violation introduite par les fichiers
      de test ajoutés (new code propre)
- [ ] Aucune régression : la suite complète reste verte (hors rouges
      pré-existants documentés)

## Manual Test Plan

- `cd Api/Mail`
- `dotnet build HealthPlatform.Api.Mail.sln --configuration Release` → 0 erreur
- `dotnet test HealthPlatform.Api.Mail.sln --configuration Release` → 0 échec
  hors les 3 rouges pré-existants documentés
- Ouvrir le dashboard SonarQube `http://localhost:9001/dashboard?id=healthplatform`
  et vérifier :
  - la **couverture globale ≥ 83%** (vs 77.4% avant la task),
  - 0 nouveau bug / vulnérabilité / code smell,
  - le détail par couche (Domain / Application / Infrastructure / Api) en
    progression.
- Parcourir le journal d'itérations de la task et vérifier la cohérence
  couverture avant/après par itération.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — outillage qualité interne, aucun volet
  métier Ségur modifié.
- **Vague Ségur** : hors Ségur — dette technique / robustesse plateforme.
- **Exigences DSR honorées** : non applicable — aucun comportement métier
  modifié (tests uniquement).
- **INS** : non applicable — aucune manipulation de données patient réelles ;
  les fixtures utilisent des INS/NIR **factices** (garde-fou 4).
- **Authentification PS** : inchangée — aucun code de production touché.
- **Habilitations** : non applicable.
- **Interop CI-SIS** : non applicable — les tests CDA réutilisent les samples
  anonymisés existants, aucun échange modifié.
- **Tracé PGSSI-S** : inchangé — aucun évènement métier ajouté ni retiré.
- **Consentement patient** : non applicable.
- **Référentiels métier** : aucun.
- **Hébergement HDS** : oui — environnement existant, périmètre inchangé ;
  une couverture de tests renforcée consolide la fiabilité du service
  (disponibilité / non-régression sur un système manipulant des DSCP).
- **AIPD / impact RGPD** : inchangé — aucun traitement modifié ; vigilance :
  aucune donnée personnelle réelle dans les jeux de test (anonymisation,
  PGSSI-S § données de test).

### DOD santé (items applicables)
- [ ] Aucune donnée de santé réelle (INS, NIR, contenu CDA nominatif,
      adresse MSSanté réelle de PS) dans les fixtures et fichiers de test
      ajoutés

## Journal d'itérations

_(rempli par `/develop` au fil des itérations)_

| Itération | Couverture avant | Classes traitées | Tests ajoutés | Couverture après |
|-----------|------------------|------------------|---------------|------------------|
| —         | 77.4%            | —                | —             | —                |

## Branches
- `api-mail` (pushed) : chore/task-067-test-coverage-raise — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/chore/task-067-test-coverage-raise
- `dtos-mss` (pushed, auto-included) : chore/task-067-test-coverage-raise — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/chore/task-067-test-coverage-raise
