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
