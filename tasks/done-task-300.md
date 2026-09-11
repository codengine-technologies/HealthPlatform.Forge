# todo-task-300.md — Les tests d'api-mail ne gardent rien : la CI ne les exécute que sur `master`, et la suite d'intégration est rouge 43 % du temps

**Repos**: api-mail
**Dependencies**: —
**Epic**: E016
**EpicTitle**: Tests d'intégration à serveur de messagerie réel
**Single frontend**: true
**Priorité**: **1** — cette US ne crée aucun test. Elle rend opposables ceux
qui existent déjà. Tant qu'elle n'est pas livrée, toute US de l'EPIC E016
ajoute des tests que **rien** n'exécute sur le chemin normal de la forge.

> **Origine** : audit de l'exploitation des tests d'intégration api-mail du
> 2026-09-11. Mesures reproduites ci-dessous, toutes vérifiables sans banc.

## Objective

Que les **97 tests qui consomment un vrai serveur IMAP/SMTP** gardent
effectivement quelque chose : qu'ils s'exécutent en intégration continue sur
`develop` — le chemin que prennent **toutes** les PR de la forge — et qu'un
rouge y soit un signal exploitable au lieu d'un bruit de fond qu'on apprend à
ignorer.

### Ce qui a été mesuré (2026-09-11)

| Grandeur | Valeur mesurée | Source |
|---|---|---|
| Tests à serveur réel exécutés en une passe | **97 / 97 verts** — 74 s puis **51 s** en re-mesure sur `cf685ac` (migration xUnit v3), images déjà tirées | `dotnet test --filter` sur les collections `UseCases`, `Services.Imap`, `BackgroundQueueDrainTests`, `BenchSmokeTests` |
| dont consommant réellement IMAP | **87** (97 − 8 `ContactsUseCaseTests` − 2 smoke SMTP seuls) | résolution DI des suites |
| Part dans la suite du repo | **2,2 %** (87 sur 3 993 `[Fact]`/`[Theory]`) | comptage par projet |
| Coût marginal d'un test à serveur réel | **0,11 s** (`ImapFolderService`, 12 tests / 1,3 s) à **0,25 s** (`ImapService`, 14 / 3,5 s) | dépouillement `.trx` |
| Exécutions de `mss.mail.integration.tests` journalisées | **30**, dont **13 rouges (43 %)**, médiane **96 s** | `metrics/timings.jsonl` |
| Tests exécutés en CI sur une PR vers `develop` | **0** | `.github/workflows/dotnet.yml:34` |

**Le défaut de fond.** `.github/workflows/dotnet.yml:34` porte
`if: github.ref == 'refs/heads/master' || github.base_ref == 'master'` sur
l'étape `Test`. Or la forge ouvre **toutes** ses PR vers `develop` (règle 5) et
`master` ne reçoit que des releases. Conséquence : la CI d'api-mail **build**
sur le chemin normal et ne **teste** jamais. Les 97 tests à serveur réel ne
tournent que sur le poste du développeur — et y sont rouges 4 fois sur 10, ce
qui achève de les retirer du rôle de barrière.

**Pourquoi les deux moitiés vont ensemble.** Rétablir le gate sans trier les
rouges connus donnerait une CI rouge en permanence, donc désactivée sous huit
jours. Trier les rouges sans rétablir le gate ne change rien. Il faut les deux
dans la même US, dans cet ordre : trier, puis brancher.

### Contenu attendu

1. **Nommer la population.** `[Trait("Server", "real")]` sur les 13 suites qui
   démarrent Dovecot ou GreenMail (collections `ImapServices` et `UseCases`,
   plus les 3 `*BenchSmokeTests`). Cible désormais adressable :
   `dotnet test --filter "Server=real"`. Sans ce trait, on ne peut ni exiger
   cette population en CI, ni mesurer son coût à part, ni la restituer.
2. **Registre de quarantaine explicite.** `tests/quarantine.md` plus le trait
   `[Trait("Quarantine", "task-NNN")]`. Une entrée = un test, **sa task
   d'origine** et la nature constatée du rouge. Le gate CI exclut
   `Quarantine`, et **rien d'autre**. Le modèle est déjà dans le repo : les
   `ExpectedErrorFragments` de `IntegrationTestBase` exigent une justification
   écrite par exemption — même exigence ici, pour la même raison (une liste
   sans justification grandit jusqu'à tout couvrir).
3. **Établir la liste réelle des rouges**, en exécutant la suite complète
   trois fois de suite et en consignant les résultats dans ce task file. Un
   test rouge **une fois sur trois** est un flaky (quarantaine + task) ; rouge
   **trois fois sur trois** est un défaut (quarantaine + task, priorité plus
   haute). Aucun test n'entre en quarantaine sans cette mesure.
4. **Rétablir le gate CI.** Retirer la condition `master` de l'étape `Test` et
   la remplacer par une exécution en deux temps : la population ordinaire,
   puis la population `Server=real`, les deux hors quarantaine, les deux
   capables de faire échouer la CI. Docker est présent sur `ubuntu-latest`,
   donc Testcontainers y tourne ; la première exécution paiera le tirage des
   images (`dovecot:2.3.21`, `greenmail:2.1.3`, `pgvector:pg16`,
   `redis:7-alpine`).
5. **Généraliser le filet d'erreurs journalisées.** Les suites `Server=real`
   héritent de `IntegrationTestBase` (adoption aujourd'hui partielle et
   assumée). Chaque `ExpectedErrorFragments` ajouté porte sa justification
   écrite dans la classe qui le déclare.

### Hors périmètre (explicite)

- **Corriger les flakies mis en quarantaine.** Chacun sort avec sa propre
  task, priorisée sur la nature du rouge. Cette US les **identifie** et les
  **isole** ; elle n'en répare aucun.
- Toute extension de la couverture à serveur réel — objet de
  `todo-task-301` à `todo-task-304`.
- Le parallélisme de la suite (`xunit.runner.json`) — il appartient à
  `todo-task-301`, qui partage le harnais ; l'activer avant rendrait le
  parallélisme suspect de tous les flakies préexistants.

## Definition of Done

- [ ] Build passes on api-mail (0 errors)
- [ ] Tests pass (0 failures) hors quarantaine déclarée
- [ ] `[Trait("Server","real")]` posé sur les 13 suites qui démarrent Dovecot
      ou GreenMail ; le filtre `Server=real` sélectionne **exactement
      97 tests** (nombre à revalider si une suite est ajoutée dans la même PR)
- [ ] `tests/quarantine.md` existe et chaque entrée porte : nom complet du
      test, task d'origine, nature du rouge (flaky / défaut), fréquence
      mesurée sur 3 exécutions
- [ ] Le trait `Quarantine` est le **seul** motif d'exclusion du gate — aucun
      filtre de la CI n'exclut un projet, un namespace ou une catégorie
      entière
- [ ] `.github/workflows/dotnet.yml` : l'étape `Test` n'a plus de condition
      sur `master` et fait échouer la CI en rouge
- [ ] Les 3 exécutions de calibrage sont consignées dans ce task file
      (tableau test × exécution)
- [ ] Les suites `Server=real` héritent de `IntegrationTestBase`, chaque
      exemption justifiée en commentaire
- [ ] Aucune donnée de santé ni identifiant réel dans les journaux de CI

## Manual Test Plan

- **Vérifier le gate localement** : `cd Api/Mail` puis
  `dotnet build tests/mss.mail.integration.tests/mss.mail.integration.tests.csproj`,
  puis `dotnet test tests/mss.mail.integration.tests --no-build --filter "Server=real"`.
  Docker doit tourner (`docker ps`).
- **Ce que l'humain doit voir** : `réussite : 97, échec : 0`, en ~75 s, et
  4 conteneurs apparus puis disparus pendant l'exécution (`docker ps` pendant
  le run → `dovecot`, `greenmail`, `pgvector`, `redis`).
- **Vérifier la quarantaine** : le filtre `Quarantine~task` sélectionne
  exactement les tests listés dans `tests/quarantine.md`, ni plus ni moins.
- **Vérifier la CI** : ouvrir la PR de cette task vers `develop` et constater
  dans l'onglet Actions que l'étape `Test` **s'exécute** (elle était
  auparavant sautée) et qu'elle est verte.
- **Contre-épreuve du gate** : casser volontairement une assertion d'un test
  `Server=real` en local, pousser sur la branche, constater la CI rouge, puis
  revenir en arrière. C'est la seule preuve que le gate garde quelque chose.
- **Données de test** : 100 % synthétiques (corpus `MailboxCorpus`,
  utilisateurs virtuels `loadtest-{n}@loadtest.local`).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — outillage de vérification interne du service
  MSSanté
- **Exigences DSR honorées** : non applicable — aucune exigence DSR ne porte
  sur la chaîne d'intégration continue ; la US sert la non-régression du
  service rendu au PS
- **INS** : non applicable — le corpus de test est synthétique et ne porte
  aucun INS, NIR ni NIA
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : aucun évènement métier nouveau. Les journaux de CI ne
  doivent porter aucune donnée de santé — garantie par un corpus synthétique
  et par le RPPS fictif `99700000042` déjà en place dans le harnais
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non — exécution en CI GitHub sur données synthétiques
  exclusivement ; aucune DSCP ne quitte l'environnement
- **AIPD / impact RGPD** : inchangée — aucun traitement nouveau

## Branches

- `api-mail` (pushed) : `feat/task-300-ci-gate-tests-serveur-reel` — base `origin/develop` @ 5855604
- `dtos-mss` (pushed, auto-inclus) : `feat/task-300-ci-gate-tests-serveur-reel` — base `origin/develop` @ f20f310 (aucun changement de contrat attendu, pas de PR si sans commit)

> Base de mesure : `cf685ac` (migration xUnit v3). `5855604` (task-295, sonde de login
> PostgreSQL du banc) ne touche ni `tests/mss.mail.integration.tests/` ni `.github/` —
> la référence « 97 tests à serveur réel » reste valide sur cette base.

## Timings

*(généré par `tools/timing/report.sh --task task-300 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 1 min 26 s | — | — | — | — |
| /develop | ok | 11 min 17 s | 1 (24 s) | 3 (4 min 56 s) | — | api-mail 1B/3T |
| /sonar | skipped | 26 s | — | — | — | aucun code C# de production dans le diff (tests + workflow + md) |
| /lint-angular | skipped | 1.9 s | — | — | — | client-angular non listé dans **Repos** (api-mail seul) |
| /lint-mobile | skipped | 2.0 s | — | — | — | client-mobile non listé dans **Repos** (api-mail seul) |
| /verify-visual | skipped | 2.2 s | — | — | — | aucun écran mobile touché |
| /review | ok | 4 min 09 s | 1 (9.7 s) | 1 (1 min 43 s) | — | api-mail 1B/1T |
| /tech-writer | ok | 2 min 23 s | — | — | — | — |
| **Total cycle** | | **19 min 48 s** | **2 (33 s)** | **4 (6 min 40 s)** | **0 (0.0 s)** | |

## Develop log

### Ce qui a été fait

1. **`[Trait("Server", "real")]` posé sur 16 classes** — les 13 suites des
   collections `ImapServices` (4) et `UseCases` (9), plus les 3
   `*BenchSmokeTests`. Littéraux et non constantes : c'est la convention déjà
   en place dans le repo (`[Trait("Category", "Integration")]`,
   `[Trait("Feature", "AI")]`), et la cohérence vaut mieux qu'une abstraction
   nouvelle pour 16 occurrences.

   > ⚠️ **Correction d'un chiffre du DOD.** Le DOD dit « les 13 suites […]
   > plus les 3 `*BenchSmokeTests` » : 13 est le compte des deux collections
   > (4 + 9), le total à étiqueter est donc **16**. Le critère qui lie
   > réellement est le suivant — `Server=real` sélectionne **exactement 97** —
   > et il est tenu.

2. **Les 3 `*BenchSmokeTests` héritent désormais de `IntegrationTestBase`.**
   Les 13 autres en héritaient déjà. **Aucune exemption
   `ExpectedErrorFragments` n'a été nécessaire** : les trois exécutions de
   calibrage sont vertes avec le filet actif, y compris
   `WildcardAuth_AcceptsAnyUser_AndRejectsWrongPassword` qui éprouve pourtant
   un refus d'authentification.

3. **Gate CI rétabli** (`.github/workflows/dotnet.yml`) : la condition
   `github.ref == 'refs/heads/master' || github.base_ref == 'master'` est
   retirée, et l'étape `Test` est scindée en deux étapes gatantes — hors
   serveur réel, puis serveur réel (Testcontainers). Les deux excluent
   `Quarantine!~task` et **rien d'autre**.

4. **`tests/quarantine.md`** posé : contrat, procédure d'entrée/sortie, et le
   tableau — **vide**.

### Les 3 exécutions de calibrage (2026-09-11, base `5855604`)

`dotnet test HealthPlatform.Api.Mail.sln --no-build`, trois fois de suite :

| Projet | Passe 1 | Passe 2 | Passe 3 |
|---|---|---|---|
| `mss.mail.domain.tests` | 167 ✓ | 167 ✓ | 167 ✓ |
| `mss.mail.infrastructure.tests` | 487 ✓ | 487 ✓ | 487 ✓ |
| `mss.mail.application.tests` | 2 400 ✓ | 2 400 ✓ | 2 400 ✓ |
| `mss.mail.api.tests` | 829 ✓ | 829 ✓ | 829 ✓ |
| `mss.mail.integration.tests` | 471 ✓ / 16 ignorés | 471 ✓ / 16 ignorés | 471 ✓ / 16 ignorés |
| **Total** | **4 370, 0 échec** | **4 370, 0 échec** | **4 370, 0 échec** |

**Résultat : liste de quarantaine vide.** Aucun test n'a été rouge, sur aucune
des trois passes. Les 16 ignorés sont des `Assert.SkipUnless` explicites
(Ollama absent, chemins Windows-only), pas des rouges.

**Ce que ce résultat ne dit pas.** Il ne dit pas que les flakies historiques
sont corrigés : `metrics/timings.jsonl` porte 30 exécutions de
`mss.mail.integration.tests` dont 13 rouges (43 %), sur des bases antérieures.
Il dit que **sur `5855604`, aujourd'hui, la suite est verte** — donc que le
gate peut être armé sans exclusion, ce qui était l'inconnue de cette US.

### Contre-épreuves du mécanisme de quarantaine

Un registre vide ne prouve rien tant que le mécanisme n'a pas été exercé. Les
deux risques ont été levés empiriquement :

| Contre-épreuve | Attendu | Mesuré |
|---|---|---|
| `--filter "Server=real"` | population serveur réel | **97** |
| `"Server=real&Quarantine!~task"`, registre vide | **97** (clause inerte sans trait) | **97** |
| `"Server!=real&Quarantine!~task"`, registre vide | 97 + N = suite complète | **4 273** (→ 4 370) |
| idem après étiquetage d'**un** test | **96** | **96** |

La deuxième ligne était le vrai risque : si `Quarantine!~task` avait exclu les
tests **dépourvus** du trait, le gate aurait exécuté zéro test en silence —
soit exactement le défaut que cette US corrige, sous une autre forme.
L'étiquette de vérification a été retirée (`grep task-999` → aucune trace).

### Note de mesure

La suite compte **4 370 cas de test** exécutés pour **3 993 déclarations**
`[Fact]`/`[Theory]` — l'écart vient des lignes de données des `[Theory]`. Les
deux chiffres sont justes, ils ne mesurent pas la même chose ; le tableau
d'origine de cette US citait le compte de déclarations.

### Passe qualité `/simplify` (§Q)

Exécutée sur le diff vs `develop` : **aucun cleanup appliqué**. Le diff est
constitué d'attributs de test, d'un héritage de classe de base et d'un fichier
de workflow — aucune duplication à factoriser, aucune abstraction à extraire
qui ne dégraderait pas la cohérence avec la convention existante. Pas de
re-validation build+test nécessaire (règle : re-valider seulement si des
cleanups sont appliqués). `dtos-mss` : hors passe qualité par construction
(porteur de contrat), et sans commit sur cette task.

## Sonar log

**Skip propre — aucun code C# de production dans le diff.**

`git diff --name-only origin/develop...HEAD` sur `api-mail` ne rend **aucun**
fichier `src/**/*.cs`. Le diff se compose de : 16 attributs `[Trait]` sur des
classes de test, 3 héritages de classe de base de test, un fichier de workflow
GitHub Actions et un `tests/quarantine.md`. Aucune issue Sonar ne peut être
attribuée à cette task, et aucun KPI ne peut bouger de son fait.

| KPI | Baseline | Final | Quality Gate |
|---|---|---|---|
| — | non mesuré (skip) | non mesuré (skip) | non évalué |

> **Précision sur l'infrastructure** : les conteneurs `sonarqube` et
> `sonarqube_db` sont arrêtés (`Exited (255)`, il y a 2 jours) et
> `localhost:9001` ne répond pas. **Ce n'est pas le motif du skip** — le motif
> est l'absence de code de production dans le diff, et il tient serveur allumé
> ou éteint. La distinction compte : un skip pour panne d'outillage serait un
> `questions/`, un skip pour périmètre vide est le fonctionnement normal de
> l'étape. Pour les tasks suivantes de l'EPIC E016 qui toucheront du code de
> production (`task-303` notamment), relancer l'infra :
> `docker start sonarqube_db && sleep 30 && docker start sonarqube`.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/230 — label `awaiting-human-merge`
- `dtos-mss` : **aucune PR** — 0 commit sur la branche (branche auto-incluse par `/start`, aucun changement de contrat nécessaire)

Run CI de la PR : 34594564320 — c'est **lui** qui valide le livrable de cette US
(les deux étapes `Test` doivent s'exécuter, alors qu'elles étaient sautées).

## Code Review Summary

**APPROVED** — 21 fichiers revus, 0 blocage, 1 suggestion non bloquante.

| Fichier / zone | Verdict |
|---|---|
| `.github/workflows/dotnet.yml` | ✅ deux étapes gatantes, commentaire portant la mesure d'origine. ⚠️ la durée de CI va croître (tirage des images au premier run) — coût assumé de la US |
| 16 fichiers de test (attribut `[Trait]`) | ✅ mécanique ; littéraux cohérents avec la convention du repo |
| 3 `*BenchSmokeTests` (héritage `IntegrationTestBase`) | ✅ validé par 4 exécutions complètes vertes, filet d'erreurs actif |
| `tests/quarantine.md` | ✅ contrat explicite, contre-épreuves reproductibles |

**Validation** : build 0 erreur ; `dotnet test` solution **4 370 tests, 0 échec**
(4ᵉ exécution verte consécutive). `develop` n'avait pas bougé depuis la base —
aucun merge de synchronisation nécessaire.
