# todo-task-082.md — Campagne de couverture de tests backend : objectif 90 %

**Repos**: api-mail
**Dependencies**: aucune
**Epic**: E009

> US mono-repo justifiée : chantier qualité **tests-only** sur `api-mail`.
> Aucun fichier de production modifié (garde-fou DOD, comme task-067).
> Pas de `.feature` (BDD déprécié, règle 1) — comportement déjà couvert,
> on ajoute uniquement des tests unitaires et d'intégration.

## Objective

Porter la couverture de code globale SonarQube du backend `api-mail` de
**85,4 % à ≥ 90 %**, en ajoutant les tests manquants **sans modifier une
seule ligne de code de production** (`git diff -- src/` doit rester vide).

Suite à la campagne task-067 (77,4 % → 83,3 %) et à un premier incrément
opportuniste (84,4 % → 85,4 %, voir ci-dessous), les gros gisements
restants ne sont **pas** couvrables en pur unitaire mocké : ils exigent des
**tests d'intégration Postgres / pgvector via Testcontainers** (le harnais
`PostgreSqlFixture` existe déjà dans `mss.mail.integration.tests`).

### Incrément déjà réalisé (branche `chore/coverage-90`)

Un premier lot de **+57 tests** (3 commits poussés sur `chore/coverage-90`,
84,4 % → 85,4 %) est déjà disponible et **doit être intégré** à cette task
(soit en repartant de cette branche au `/start`, soit en cherry-pick) :

- `f2b7b9e` — base d'embedding (`BaseEmbeddingProviderService`), boucles
  hébergées `BackgroundImapConnectionMaintenanceService` /
  `MailClientSessionCleanupService` (classes à 0 %), happy-paths
  `ImapFolderService` (create / rename / delete / move / bulk-move / cache hit)
- `c5a657c` — branches d'entrée `ImapConnectionService` (domaine inconnu,
  token vide, réutilisation de connexion)
- `6dabd53` — opérations draft / sent / tag / thread d'`ImapService`

> Note de séquencement pour `/start` : si la branche `chore/coverage-90`
> est reprise telle quelle, le pré-vol « tous les repos sur develop » ne
> s'applique pas à cette branche existante — à arbitrer par l'humain
> (reprendre `chore/coverage-90` OU repartir de `develop` et re-merger les
> 3 commits). Le plus simple : renommer/continuer `chore/coverage-90`.

## Gisements restants (analyse SonarQube 2026-06-13, par lignes non couvertes)

| Fichier | Couverture | Lignes non couvertes | Levier |
|---|---|---|---|
| `src/Application/Services/Implementation/ImapService.cs` | 72,3 % | 332 | Unitaire (mockable, mais MailKit expose des extension methods non-mockables → plafond) + intégration |
| `src/Infrastructure/Repository/MailRepository.cs` | 85,2 % | 207 | **Intégration Testcontainers** |
| `src/Infrastructure/Repository/BaseRepository.cs` | 22,5 % | 131 | **Intégration Testcontainers** (bootstrap Npgsql par-tenant) |
| `src/Infrastructure/Repository/SemanticSearchRepository.cs` | 80,7 % | 79 | **Intégration Testcontainers + pgvector** |
| `src/Api/Controllers/V1/AiDiagnosticsController.cs` | 67,2 % | 57 | Intégration TestServer |
| `src/Application/Services/Implementation/SemanticSearchService.cs` | 83,0 % | 52 | Unitaire (embeddings substitués) |
| `src/Application/Services/Implementation/SmtpConnectionFactory.cs` | 62,2 % | 50 | Difficile (TLS/SMTP réel) — best-effort |
| Reste (`BackgroundSyncManager`, `CdaParsingService`, controllers divers, …) | < 90 % | ~290 cumulés | Mixte unitaire / intégration |

**Maths SonarQube** : la métrique `coverage` mélange lignes **et** conditions.
Pour passer de 85,4 % à 90 %, il faut réduire le total (lignes+conditions)
non couvertes de ~3 416 à ≤ 2 336, soit **~1 080 lignes/conditions à couvrir**
(estimé ~250-300 tests). C'est un chantier multi-itérations, à la hauteur de
task-067.

## Approche (itérative, via `code-coverage-skill` / `sonar-skill`)

1. Repartir de l'incrément `chore/coverage-90` (85,4 %).
2. Boucle (cible 90 % ou plafond raisonnable d'itérations) :
   a. Analyse SonarQube complète (`sonar-skill`).
   b. Sélection des fichiers < 90 % par lignes/conditions non couvertes.
   c. Écriture des tests : **unitaires** (NSubstitute + xUnit `Assert`, conventions repo)
      pour l'Application/Api mockable ; **intégration Testcontainers**
      (`PostgreSqlFixture`, pgvector) pour les repositories Infrastructure.
   d. Build + suite verte (hors flaky pré-existants documentés).
   e. Re-analyse, mesure de la progression.
3. Priorité aux fichiers à fort volume de lignes non couvertes (impact maximal).

## Rescope (2026-06-14) — cible 90 % → 85,4 %

Décision humaine : **figer le gain acquis** (84,4 % → 85,4 %, +57 tests) et
ouvrir la PR maintenant, plutôt que de poursuivre une campagne chirurgicale
de couverture de branches au rendement très faible (~2 lignes / 12 tests,
cf. itération 2 dans `questions/task-082.md`).

Le reste (~1 080 lignes/conditions pour atteindre 90 %, concentré dans
`MailRepository`/`BaseRepository`/`SemanticSearchRepository` en intégration
Testcontainers + chemins IMAP via extension methods MailKit non-mockables)
est **replanifié hors task-082**. Cible DOD ajustée à la valeur atteinte.

## Definition of Done

- [x] Build passes : `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln --configuration Release` (0 erreur — vérifié /review 2026-06-14)
- [x] Tests pass : `dotnet test HealthPlatform.Api.Mail.sln --configuration Release` (2658 réussis, 16 skip AI, 1 échec = flaky IMAP cancel pré-existant documenté — vérifié /review 2026-06-14)
- [x] **Couverture globale SonarQube ≥ 85,4 %** (cible **rescopée** le 2026-06-14 de 90 % → 85,4 %, valeur réellement atteinte — voir note de rescope ci-dessous ; vérifiée par analyse `sonar-skill`)
- [x] **Zéro fichier de production modifié** : `git diff origin/develop...HEAD -- src/` est **vide** (garde-fou tests-only — vérifié /review 2026-06-14)
- [x] Tests d'intégration Testcontainers ajoutés pour `MailRepository` (12 tests verts) — `BaseRepository` / `SemanticSearchRepository` **replanifiés hors task-082** (it. 2 : déjà couverts transitivement, restant = couverture de branches chirurgicale infaisable au rendement actuel, voir `questions/task-082.md`)
- [x] Aucun test trivial (sans assertion réelle) — chaque test couvre un comportement (vérifié au code review)
- [~] Quality Gate SonarQube — chantier tests-only, aucune dette de production introduite (`src/` diff vide) ; re-run complet `sonar-skill` à faire par l'humain au Manual Test Plan
- [x] Journal d'itérations rempli (couverture avant/après, classes traitées, tests ajoutés)
- [x] Aucune donnée de santé réelle dans les fixtures de test (INS factices uniquement — vérifié au code review)

## Manual Test Plan

- `cd Api/Mail`
- Lancer l'analyse de couverture complète via le `sonar-skill` (begin → build
  Release → 5 projets de test avec couverture OpenCover → end).
- Ouvrir le dashboard SonarQube : http://localhost:9001/dashboard?id=healthplatform
- Vérifier que la métrique **Coverage ≥ 90 %** et que le Quality Gate est **OK**.
- Vérifier `git diff origin/develop...HEAD -- src/` : **aucune** modification de
  code de production (uniquement `tests/**`).
- Lancer la suite complète en Release et confirmer qu'aucun échec n'apparaît
  hors les rouges flaky/environnementaux déjà documentés (middleware DB-name
  Release, IMAP cancel, MailExport PDF, patient INS pagination, Cda/Markdown
  metrics parallèles).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — outillage qualité interne (couverture de tests)
- **Vague Ségur** : hors Ségur — aucune exigence DSR (renforcement de tests d'un comportement déjà livré)
- **Exigences DSR honorées** : non applicable — chantier qualité, aucun comportement métier modifié
- **INS** : non applicable — les fixtures n'utilisent que des INS factices ; aucun enregistrement/envoi patient réel
- **Authentification PS** : non applicable — aucun flux d'authentification modifié
- **Habilitations** : non applicable
- **Interop CI-SIS** : non applicable — aucun échange CDA/FHIR modifié
- **Tracé PGSSI-S** : non applicable — aucun évènement de journalisation ajouté ni retiré
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement HDS existant inchangé (tests uniquement)
- **AIPD / impact RGPD** : inchangé — aucun nouveau traitement ; données de test factices

### DOD santé (items applicables)
- [ ] Aucune INS réelle dans les fixtures (INS factices type 9000000000000x uniquement)
- [ ] Aucune donnée de santé réelle dans les tests ni dans les logs qu'ils déclenchent

## Branches
- `api-mail` (pushed) : feat/task-082-coverage-90-campaign — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-082-coverage-90-campaign
  - inclut déjà l'incrément `chore/coverage-90` (3 commits, +57 tests, 85,4 %) mergé en tête de branche
- `dtos-mss` (pushed, auto-incluse) : feat/task-082-coverage-90-campaign — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-082-coverage-90-campaign (restera vide — task tests-only sur api-mail)

## Develop log (itération 1 — checkpoint)

- Repos touched : api-mail (tests uniquement). dtos-mss : branche auto-incluse vide.
- DTOs / Interop published : aucun (task tests-only, `git diff -- src/` vide).
- Incrément livré sur la branche `feat/task-082-coverage-90-campaign` (3 commits, +57 tests) :
  - couverture globale **84,4 % → 85,4 %** (mesuré SonarQube, 2 analyses)
  - classes passées de 0 % à couvertes : `BaseEmbeddingProviderService`, `BackgroundImapConnectionMaintenanceService`, `MailClientSessionCleanupService`
  - `ImapFolderService` 66,8 % → ~90 % (happy-paths create/rename/delete/move/bulk/cache)
  - `ImapService` 68,4 % → 72,3 % (draft/sent/tag/thread + early branches)
  - `ImapConnectionService` branches d'entrée
- Build / tests : ✓ suite verte (hors flaky pré-existants documentés). Tous les 57 tests passent.
- DOD self-check : `git diff -- src/` **vide** ✓ ; couverture **85,4 %** (cible 90 % **non encore atteinte**).

### Pourquoi un checkpoint et pas un hand-off /review

La cible ≥ 90 % n'est **pas atteignable en une passe `/develop`** — c'est un
chantier multi-itérations (le DOD lui-même le scope ainsi). Constat technique
après 2 analyses SonarQube :

- Les surfaces **mockables faciles sont déjà largement couvertes** (ex.
  `SemanticSearchService` a déjà ~38 tests pour 52 lignes restantes = branches
  privées profondes ; `BackgroundSyncManager` 17 tests ; etc.). Le rendement
  marginal du pur unitaire mocké est désormais faible.
- Le gros du restant (~1 080 lignes/conditions à couvrir pour 90 %) est concentré
  dans **3 repositories Infrastructure** (`MailRepository` 207, `BaseRepository`
  131 à 22,5 %, `SemanticSearchRepository` 79) → exige des **tests d'intégration
  Postgres/pgvector Testcontainers** (Docker requis), + les chemins IMAP de
  `ImapService` qui passent par des **extension methods MailKit non-mockables**
  par NSubstitute (plafond du testable en unitaire).

Chiffrage : ~250-300 tests supplémentaires + plusieurs cycles d'analyse de
~7 min chacun + démarrages de conteneurs Docker. C'est l'ampleur de task-067
(une task complète, 5 itérations).

### Pour reprendre (itération 2+)

1. `cd Api/Mail`, branche `feat/task-082-coverage-90-campaign` (contient déjà l'incrément).
2. Priorité aux tests d'**intégration Testcontainers** sur `MailRepository`,
   `BaseRepository`, `SemanticSearchRepository` (harnais `PostgreSqlFixture` +
   pattern `MailRepositoryTagDraftCoverageTests` task-067, déjà en place).
3. Compléter `ImapService` / controllers (`AiDiagnosticsController` 57) en
   intégration TestServer là où l'unitaire plafonne.
4. Boucle `sonar-skill` : analyse → cibler les fichiers < 90 % → tests → re-analyse,
   jusqu'à couverture ≥ 90 % et `git diff -- src/` toujours vide.
5. Quand 90 % atteint → `/review task-082`.

> Voir `questions/task-082.md` pour le détail de reprise.

## PRs

- **api-mail** : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/104 — label `awaiting-human-merge`
- **dtos-mss** : aucune PR (branche auto-incluse, 0 commit — task tests-only sur api-mail)

## Code Review Summary

Verdict : **APPROVED** (7 fichiers de test relus, 1 suggestion non-bloquante, 0 bloquant).

- Build Release ✅ 0 erreur · Tests Release ✅ 2658 réussis (1 flaky IMAP cancel pré-existant documenté, 16 skip AI)
- `git diff -- src/` vide ✅ (garde-fou tests-only respecté)
- Qualité : assertions réelles, happy-paths + erreurs, données factices, conventions repo OK
- ⚠️ Suggestion : tracker le bug latent `MarkReadReceiptSentAsync` (schéma EF `timestamptz` ↔ FluentMigrator `timestamp`, cf. task-078) dans une task dédiée — hors périmètre tests-only.

## Merged

- **Date** : 2026-06-14
- **api-mail** : squash `f3201ba` — PR #104 closed (`gh pr merge --squash --delete-branch`, remote branch deleted, local branch preserved)
- **dtos-mss** : aucune PR (branche auto-incluse vide) — rien à merger
- **client-angular** : non listé — managed manually by the human
- **develop CI** : ✓ green — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/27504898295
