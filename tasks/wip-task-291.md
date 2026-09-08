# todo-task-291.md — La suite de tests d'api-mail est non déterministe : un test différent échoue à chaque exécution complète

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009

> **Origine** : constaté pendant la campagne task-184 du 2026-09-06. Quatre
> exécutions complètes de `dotnet test HealthPlatform.Api.Mail.sln`, quatre
> résultats différents, **aucun rapport avec le code modifié** (la task ne
> touchait que la couche API et son masquage de journaux).

## Objective

Rendre `dotnet test HealthPlatform.Api.Mail.sln` **déterministe**. Aujourd'hui
il échoue presque à chaque exécution complète, sur **un test différent à chaque
fois**, et chacun de ces tests est **vert quand on le lance seul**.

Ce n'est pas un désagrément d'ergonomie : c'est un **garde-fou qui ne garde
plus rien**. Une suite qui rougit au hasard apprend à qui la lit à ignorer un
rouge — et le jour où un vrai défaut passe, il sera classé « encore le flaky »
sans être ouvert. La campagne task-184 a déjà consommé quatre re-exécutions
d'isolation pour établir, à chaque fois, que l'échec n'était pas le sien.

### Preuve — le relevé des quatre exécutions

Même commande, même commit, à quelques minutes d'intervalle :

| # | Assembly | Test qui échoue |
|---|---|---|
| 1 | `mss.mail.infrastructure.tests` | `MailRepositoryEnrichPersistInstrumentationTests.A_deduplicated_mail_is_measured_too_instead_of_vanishing_from_the_series` |
| 2 | `mss.mail.infrastructure.tests` **+** `mss.mail.integration.tests` | le même, **plus** `SemanticSearchRepositoryIntegrationTests.SearchByFiltersAsyncShouldFilterBySubjectAsync` |
| 3 | `mss.mail.application.tests` | `EnrichmentOperationScopeTests.A_closed_scope_refuses_late_contributions` **et** `…The_total_includes_the_seeded_fetch_which_was_paid_before_the_scope_opened` |
| 4 | `mss.mail.application.tests` | `MarkdownPdfRendererTests.RenderGfmTableKeepsAllCellsInOrder` |

**Chacun de ces tests a été relancé isolément, deux fois, et est vert les deux
fois.** Le défaut n'est donc pas dans les tests pris un par un : il est dans ce
qu'ils se font subir mutuellement.

> ⚠️ **Correction d'un constat trop rapide.** Le message de commit `754a194`
> parle d'« un état partagé dépendant de l'ordre **dans cet assembly** ». C'est
> faux : le phénomène touche **trois** assemblies
> (`application`, `infrastructure`, `integration`). Une cause unique « interne à
> un assembly » est donc écartée d'emblée, et c'est ce qui rend la première
> étape de cette task nécessaire plutôt qu'évidente.

### Pistes établies — à confirmer, pas à croire

Deux constats mesurés pendant l'analyse. Ils orientent, ils ne concluent pas.

**Piste 1 — parallélisme xUnit par défaut + compteurs statiques de processus.**

- **Seul** `mss.mail.integration.tests` porte un `xunit.runner.json`, et il y
  **désactive tout** (`parallelizeAssembly: false`,
  `parallelizeTestCollections: false`, `maxParallelThreads: 1`).
- Les quatre autres assemblies (`application`, `infrastructure`, `api`,
  `domain`) n'ont **aucune** configuration : ils tournent donc avec le
  **parallélisme xUnit par défaut** — collections en parallèle,
  `maxParallelThreads` = nombre de cœurs.
- Côté production, la télémétrie repose sur des `Meter` **statiques** donc
  partagés par tout le processus :
  `src/Application/Telemetry/FeatureFlagMetrics.cs:15` et
  `src/Application/Telemetry/MailProcessingMetrics.cs:19`.
- Côté tests, **15 classes** de `application` + `infrastructure` attachent un
  `MeterListener` / `MeterProvider`.

Un `MeterListener` attaché à un `Meter` statique **voit les mesures émises par
les autres tests qui tournent en même temps**. Deux des trois familles qui
échouent sont précisément des tests d'instrumentation
(`EnrichmentOperationScope`, `MailRepositoryEnrichPersistInstrumentation`) — ce
qui est cohérent, mais ne suffit pas à conclure.

**Piste 2 — le cas `integration` a forcément une AUTRE cause.**
`SemanticSearchRepositoryIntegrationTests` vit dans le seul assembly où le
parallélisme est **déjà** désactivé. Son échec ne peut donc pas venir du
parallélisme intra-assembly. Candidat : le fixture Postgres partagé
(`[Collection("PostgreSql")]`) et des données laissées par un test voisin —
c'est un mode d'échec déjà documenté sur ce banc (les suites pgvector se
marchent sur les dimensions de vecteurs).

**Piste 3 — `MarkdownPdfRenderer` n'entre dans aucune des deux.** Le rendu PDF
ne touche ni compteur ni base. Soit une troisième cause (sensibilité au temps
ou à la charge de la machine sous parallélisme), soit un partage statique non
identifié. **À ne pas ranger de force dans les deux premières.**

### Contenu attendu

1. **Établir la ou les causes AVANT de corriger.** Trois familles, trois
   assemblies, au moins deux causes probables : un correctif appliqué sur une
   intuition rendrait la suite verte sans qu'on sache pourquoi, et la
   non-déterminisme reviendrait sous une autre forme. Le livrable de cette
   étape est **écrit** : pour chaque famille, la cause et la mesure qui
   l'établit.

   Outil recommandé : `dotnet test --logger "console;verbosity=detailed"` pour
   obtenir l'ordre réel d'exécution, et la re-exécution ciblée de la paire
   (test qui échoue + tests concurrents de la fenêtre) pour reproduire à la
   demande. **Une cause n'est établie que si l'échec est reproductible**, pas
   seulement observé.

2. **Corriger à la cause, pas au symptôme.** Les remèdes acceptables, selon ce
   que l'étape 1 établit :
   - isoler l'état partagé (fixture par collection, `Meter` injecté au lieu
     d'un statique, listener scopé) ;
   - déclarer les collections xUnit qui doivent être sérialisées ;
   - en dernier recours et **avec justification écrite**, désactiver le
     parallélisme sur l'assembly concerné — c'est le remède le plus coûteux
     (durée de suite) et le plus grossier, il n'est pas le point de départ.

   **Interdit** : `[Fact(Skip = …)]`, `[Trait("flaky")]` exclu du CI, ou un
   `retry`. Masquer le rouge est exactement le mécanisme qui a rendu ce défaut
   coûteux.

3. **Prouver le déterminisme, pas l'affirmer.** Le critère n'est pas « la suite
   est verte une fois » — elle l'est déjà une fois sur quatre. Voir la DOD.

4. **Garde-fou anti-récidive.** Le partage d'un `Meter` statique entre tests
   parallèles est une classe de défaut qui reviendra à la prochaine famille de
   compteurs. Prévoir un contrôle mécanique (test de convention, ou
   configuration explicite du parallélisme documentée par un commentaire qui
   dit *pourquoi*).

### Hors scope

- L'optimisation de la **durée** de la suite. Si le remède retenu la rallonge,
  le noter et ouvrir une task de suite — mais ne pas troquer le déterminisme
  contre de la vitesse dans cette US.
- Les flaky de la campagne de charge (harnais k6), qui ont leurs propres causes
  documentées dans le skill `loadtest-skill`.
- `SemaphoreFullException` sur `AppendToSent`, défaut connu et non corrigé, sans
  rapport.

## Périmètre — RESTREINT par arbitrage humain du 2026-09-08

> Cette task a été cadrée en supposant **une** cause. L'implémentation en a
> établi **trois**, indépendantes. `/develop` s'est arrêté en fail-fast et a
> posé la question du découpage (`questions/task-291.md`).
>
> **Décision humaine du 2026-09-08** : *« accepte A et ne crée pas de nouvelles
> tâches pour le moment »*.
>
> Le périmètre de task-291 est donc **la famille A seule**. La DOD ci-dessous
> est réécrite en conséquence — **sur décision du PO, pas par l'agent** : un
> agent qui réécrit ses propres critères pour les faire passer est exactement
> l'anti-pattern que cette task dénonce.
>
> ⚠️ **B et C ne font l'objet d'AUCUNE task, volontairement.** Leur trace vit
> donc ici et nulle part ailleurs — voir « Ce qui reste, sans task ».

## Definition of Done — famille A (périmètre accepté)

- [x] Build passes (0 errors)
- [x] **Cause de la famille A établie et écrite**, avec la mesure :
      `MailMetricsCaptureCollection` sans `DisableParallelization = true` (donc
      sérialisant ses propres classes et personne d'autre), deux `SessionLock*`
      hors de toute collection émettant sur le même meter statique, et
      `infrastructure.tests` sans aucune collection pour trois classes de
      capture. Consigné dans le code (`dd83bdc`) et dans « Causes établies ».
- [x] **Le contraste qui établit la course est mesuré** : `application.tests`
      seul est vert **5/5** (2280 tests), la **solution** — cinq assemblies en
      parallèle — sortait rouge **2/3**. La course est latente en permanence, la
      contention CPU la révèle. Piège de diagnostic consigné : rejouer
      l'assembly seul innocente à tort.
- [x] **La famille A ne réapparaît plus** : sur **16 exécutions de la solution
      après correctif** (10 consécutives sans aucun échec, puis 6 de chasse), le
      moindre échec de capture de métrique est **absent** — les 2 rouges de la
      chasse relèvent de B et C. C'est le critère honnête pour A ; voir
      « Ce qui reste » pour pourquoi « 10 verts » ne prouvait pas la suite.
- [x] Aucun test désactivé, ignoré, exclu du CI ou sous `retry` : **4123 tests
      exécutés, 16 skipped** — inchangé (4101 + 22 tests ajoutés par cette task
      et par task-184).
- [x] Garde-fou anti-récidive en place et **prouvé** :
      `MetricCaptureSerialisationScanTests` porte trois cas qui l'éprouvent
      (détecte une capture non sérialisée, ne signale pas une capture
      sérialisée, ignore un helper sans test). **Il a payé dès sa première
      exécution** en trouvant `TaggingFailureIsCountedTests`, manquée par le
      relevé manuel.
- [ ] CI `develop` verte après merge — vérifiable seulement après le merge (HAG)

**Retiré du périmètre** (relevait de B et C) : la reproductibilité à la demande
et les « 10 exécutions consécutives vertes » comme preuve d'extinction de la
suite entière. Voir ci-dessous.

## ⚠️ Ce qui reste, sans task — à ne pas perdre

**La suite restera rouge par intermittence** (~1 exécution sur 5 observée). Ce
n'est **pas** une régression du correctif A : ce sont deux causes distinctes,
identifiées, délibérément non traitées sur décision du 2026-09-08.

**Pourquoi « 10 exécutions vertes » ne prouve rien ici** : le critère a été
**atteint** (10/10, 0 échec) *puis* le 11e run est sorti rouge. Un défaut qui
frappe ~1 run sur 5 passe une fenêtre de 10 environ une fois sur trois. À
retenir pour toute future DOD de flakiness : une fenêtre de N verts ne borne
rien sans le taux d'échec de base.

### Famille B — `MarkdownPdfRendererTests` (atténuée, cause NON établie)

Deux méthodes touchées (`RenderGfmTableKeepsAllCellsInOrder`, puis
`RenderRowsWithFewerCellsThanHeaderDoesNotThrow`). **Pas la cause A** : aucune
autre classe n'utilise QuestPDF, donc aucun concurrent ne pollue un état de test
partagé. Ce qui est partagé est **global au processus et natif** —
`QuestPDF.Settings` muté par le constructeur, rendu SkiaSharp de
`GeneratePdf()` — et les assertions portent sur du **texte extrait d'un PDF**,
donc sur une mise en page sensible aux ressources.

La classe **est sérialisée**, en atténuation assumée et commentée comme telle
dans le fichier. Le symptôme devient rare ; la sensibilité reste. Reproduction à
la demande **non obtenue**.

### Famille C — fixture Postgres partagé d'`integration.tests` (NON traitée)

`SeededThreadsAreCountableTests.SeveralDistinctThreadSizesReachTheCounter` et
`SemanticSearchRepositoryIntegrationTests.SearchByFiltersAsyncShouldFilterBySubjectAsync`,
tous deux `[Collection("PostgreSql")]`.

Cet assembly a **déjà** `parallelizeTestCollections: false` : il n'y a donc
**aucune course**. C'est de l'**interférence de données séquentielle** — un test
voit les lignes semées par un voisin. Mode d'échec déjà documenté sur ce banc
(les suites pgvector se marchant sur les dimensions de vecteurs).

Le remède est l'isolation des données par test (clés uniques, ou nettoyage entre
tests) sur une suite d'intégration entière — un chantier d'un autre ordre que A.

### Accessoirement — lacune de CLAUDE.md

`interop` n'a **pas** de `.git`, exactement comme `Host/Modules` : `git -C interop`
remonte au dépôt du plan de contrôle et répond pour lui. CLAUDE.md ne porte cet
avertissement que pour `host`, donc le pré-flight de `/start` ne mesure rien pour
**`interop-cda`** non plus, sans le dire. Correctif d'une ligne, non fait.

## Manual Test Plan

1. `cd Api/Mail`
2. **Avant correctif — reproduire le défaut** :
   `for /l %i in (1,1,5) do dotnet test HealthPlatform.Api.Mail.sln`
   (ou la boucle bash équivalente). **Attendu avant correctif** : au moins une
   exécution rouge, sur un test qui varie d'une exécution à l'autre.
3. Relancer le test fautif **seul** :
   `dotnet test <assembly> --filter "FullyQualifiedName~<TestName>"`.
   **Attendu avant correctif** : vert. C'est le contraste qui signe le défaut.
4. **Après correctif** : rejouer l'étape 2 avec **10** itérations.
   **Attendu** : 10 exécutions vertes, aucun test ignoré.
5. Vérifier le nombre de tests exécutés (somme des `Total:` par assembly) :
   **≥ 4101**, donc rien n'a été mis sous le tapis.
6. Relever la durée totale de la suite avant/après et la consigner.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — task d'outillage de test, aucune
  fonctionnalité métier exposée à un PS ou à un patient
- **Vague Ségur** : hors Ségur — même raison
- **Exigences DSR honorées** : non applicable — aucune exigence DSR ne porte sur
  le déterminisme d'une suite de tests. **Indirectement** : la fiabilité du
  filet de tests conditionne toutes les vérifications PGSSI-S qui s'appuient
  sur lui (task-184 en a livré trois : masquage de journaux, scan de gabarits de
  route, scan de gabarits de log). Un rouge aléatoire les rend inopposables.
- **INS** : non applicable — aucune manipulation d'INS. Les données de test des
  suites concernées sont déjà synthétiques
- **Authentification PS** : inchangée — aucune modification du chemin
  d'authentification
- **Habilitations** : non applicable
- **Interop CI-SIS** : non applicable — aucun échange, aucun document produit
- **Tracé PGSSI-S** : non applicable — aucun évènement métier journalisé n'est
  ajouté ni retiré. ⚠️ **Vigilance** : si le remède retenu touche aux `Meter`
  statiques de `MailProcessingMetrics` / `FeatureFlagMetrics`, vérifier que la
  télémétrie de **production** reste émise à l'identique — un compteur rendu
  non statique pour faire plaisir aux tests ne doit pas cesser d'être exporté
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non — exécution locale et CI, aucune DSCP manipulée
- **AIPD / impact RGPD** : inchangé — aucun traitement de données personnelles
  créé ni modifié

## Branches

- `api-mail` (pushed) : `fix/task-291-suite-tests-non-deterministe` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-291-suite-tests-non-deterministe
- `dtos-mss` (pushed, auto-inclus) : `fix/task-291-suite-tests-non-deterministe` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/fix/task-291-suite-tests-non-deterministe
  (branche créée par convention CLAUDE.md ; **aucun changement de DTO attendu**
  pour cette task — elle restera sans commit et sans PR)

Préfixe `fix/` et non `feat/` : la task ne livre aucune fonctionnalité, elle
répare un garde-fou.

### Pré-vol du 2026-09-06

Sept repos automatisés sur `develop`, aucun sur une branche de feature. Seul
fichier non committé : `metrics/timings.jsonl`, écrit par `step.sh start` de
cette étape même.

> ⚠️ **Lacune de pré-vol constatée, hors scope de cette task.** `interop` n'a
> **pas** de `.git` — exactement comme `Host/Modules`. `git -C interop` remonte
> donc au dépôt du plan de contrôle et répond pour lui. CLAUDE.md ne porte cet
> avertissement que pour `host` : le pré-flight de `/start` ne mesure donc rien
> pour **`interop-cda` non plus**, et ne le dit pas. À corriger dans CLAUDE.md.

## Timings

*(généré par `tools/timing/report.sh --task task-291 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 59 s | — | — | — | — |
| /develop | ok | 0.4 s | — | — | — | — |
| /sonar | ok | 10 min 05 s | — | — | — | — |
| **Total cycle** | | **11 min 05 s** | **0 (0.0 s)** | **0 (0.0 s)** | **0 (0.0 s)** | |

## Causes établies — famille A

### Le détail qui manquait à task-256

`MailMetricsCaptureCollection` existait **déjà** et documentait le défaut (meter
statique + parallélisme xUnit). Il lui manquait **`DisableParallelization = true`**.

Sans ce drapeau, une `CollectionDefinition` sérialise ses **propres** classes
entre elles, mais la collection continue de tourner **en parallèle des autres
collections et de toute classe non collectée**. Les huit classes rattachées
étaient donc protégées les unes des autres — et de personne d'autre.

### Les polluantes

| Classe | Problème | Correctif |
|---|---|---|
| `SessionLockInstrumentationTests` | émet sur le meter statique via `LockObservations`, **aucune** collection | rattachée |
| `SessionLockPhaseInstrumentationTests` | idem | rattachée |
| `TaggingFailureIsCountedTests` | écoute `MailProcessingMetrics.MeterName`, **aucune** collection — **manquée par le relevé manuel**, trouvée par le garde-fou | rattachée |
| `MailRepositoryEnrichPersistInstrumentationTests` | capture, assembly **sans aucune** collection | `MetricsCaptureCollection` créée |
| `MailReadObjectCountTests` | capture via `ObjectCountCapture`, idem | rattachée |
| `DbOperationPhaseInterceptorsTests` | capture via `PhaseCapture`, idem | rattachée |

La collection d'`application.tests` ne pouvait pas servir à `infrastructure.tests` :
**une collection xUnit ne franchit pas la frontière d'assembly.**

### Le piège de diagnostic, à retenir

**Rejouer l'assembly seul « pour vérifier » innocente à tort.** Mesuré :

| Portée | Résultat |
|---|---|
| `application.tests` seul | **5/5 verts** (2280 tests) |
| solution (5 assemblies en parallèle) | **rouge 2 fois sur 3** |

La course est latente en permanence ; la contention CPU des assemblies
concurrentes est ce qui fait réellement se recouvrir les fenêtres de capture.
C'est l'erreur que j'ai commise d'abord — et elle coûte cher, parce qu'elle
conclut « pas mon problème » sur un défaut bien réel.

### Le garde-fou

`MetricCaptureSerialisationScanTests` balaie les sources **suivies par git** de
**tous** les assemblies de test et refuse une classe de test qui capture sans
être sérialisée. Scan de **sources** et non réflexion : l'usage d'un
`MeterListener` vit dans un corps de méthode, invisible sans lire l'IL.

Trois cas l'éprouvent lui-même : il détecte la forme fautive, il ne signale pas
une capture correctement sérialisée, et il ignore un helper porteur d'un
`MeterListener` mais d'aucun test (`ObjectCountCapture`, `PhaseCapture`,
`LockObservations` — ce sont leurs **utilisateurs** qu'il faut sérialiser).

## Mesures

| Grandeur | Valeur |
|---|---|
| Exécutions de la solution après correctif | **16** (10 consécutives + 6 de chasse) |
| Échecs de la famille A sur ces 16 | **0** |
| Échecs relevant de B ou C | 2 (runs 3 et 5 de la chasse) |
| Tests exécutés / skipped | **4123 / 16** — aucun test désactivé |
| Durée de la suite | inchangée (~3 min ; la sérialisation ne touche que des classes de capture, très courtes) |

Aucun `xunit.runner.json` n'a été modifié : le parallélisme reste actif partout
où il l'était. Le remède est ciblé sur les classes qui capturent, pas sur
l'assembly.

## Décision de périmètre — 2026-09-08

Arbitrage humain sur `questions/task-291.md` : **A accepté comme livrable, pas
de task de suite pour B ni C pour le moment.** La trace de B et C vit donc dans
la section « Ce qui reste, sans task » de ce fichier, et nulle part ailleurs.

## Sonar log

Analyse complète de la branche `fix/task-291-suite-tests-non-deterministe`
(après resynchronisation sur `develop`, task-186 incluse), 2026-09-08.

### KPI

| Métrique | Baseline | Final | Cible |
|---|---|---|---|
| `bugs` | 0 | **0** | 0 ✅ |
| `vulnerabilities` | 0 | **0** | 0 ✅ |
| `code_smells` | 65 | 67 | — |
| `new_bugs` | 0 | **0** | 0 ✅ |
| `new_vulnerabilities` | 0 | **0** | 0 ✅ |
| `new_code_smells` | 38 | **8** | 0 ⚠️ |
| `coverage` | 88,3 % | 88,0 % | 95 % ⚠️ |
| `new_coverage` | 90,8 % | 87,4 % | 95 % — QG OK |
| `duplicated_lines_density` | 0,4 % | 0,4 % | — |
| `reliability_rating` / `security_rating` / `sqale_rating` | — | **A / A / A** | A ✅ |
| **Quality Gate** | OK | **OK** | OK ✅ |

⚠️ **La baseline n'est pas comparable au strict** : elle provient de la dernière
analyse en date, celle du cycle de task-186, sur un périmètre de branche
différent. Les deltas de `code_smells` (+2) et de `coverage` (−0,3 pt) sont donc
**indicatifs et non attribuables** — la fusion de task-186 apporte du code de
production que la baseline ne mesurait pas au même point. Le dire plutôt que
laisser croire à une régression de cette task.

### Aucune issue n'est imputable à task-291

Les 15 code smells ouverts de la période portent tous sur du code que cette task
n'a pas écrit (`RevocationDownloadCoordinator`, `MailClientSession`,
`SentArchiveService`, `MailServerDiscovery`, `IheXdmProcessingService`, plus des
`INFO` CA14xx). **Les fichiers de task-291 n'en produisent aucun** — ce sont des
fichiers de test, analysés (seule la *couverture* exclut `**/tests/**`), et ils
sortent propres.

**Deux fausses pistes vérifiées et closes**, pour que personne ne les rechasse :

| Issue | Fichier | Verdict |
|---|---|---|
| `S125` « remove commented out code » | `RequestLoggingMiddleware.cs:115` | **CLOSED / FIXED** — déjà traitée dans task-184 |
| `S3267` « loops should be simplified with LINQ » | `SensitiveRequestDataSanitizer.cs:182` | **CLOSED / FIXED** — déjà traitée dans task-184 |

Toutes deux apparaissaient dans la liste « nouvelle période » comme entrées
historiques, ce qui les fait passer pour actionnables alors qu'elles ne le sont
plus. Contrôle : filtrer sur `status=OPEN`, pas seulement sur
`inNewCodePeriod=true`.

### Décision — early-stop, best-effort assumé

Zéro itération de nettoyage. Motif : Quality Gate **OK**, `bugs` et
`vulnerabilities` à **0**, les trois notes à **A**, et **task-291 n'introduit
aucun smell**. Les 15 restants relèvent d'autres tasks ; les corriger ici
mélangerait les périmètres (règle 6, scopes isolés) et gonflerait un diff de
task de test avec du refactoring de production sans rapport.

Les deux cibles projet non atteintes (`coverage` 88 % < 95 %, `new_code_smells`
8 ≠ 0) sont **antérieures et non imputables**. Elles restent affichées ici parce
que la règle est de toujours monitorer la qualité, jamais de clore en silence.

### Note d'outillage

`dotnet sonarscanner begin` **exige** `MSYS_NO_PATHCONV=1
MSYS2_ARG_CONV_EXCL='*'` sous Git Bash : sans eux, le `/` initial de chaque
`/k:` et `/d:` est converti et le scanner répond
« Unrecognized command line argument », puis « A required argument is missing ».
C'est le piège MSYS documenté du skill, **en sens inverse** de celui de `run.sh`
pour k6 — qui exige, lui, que ces variables soient *absentes*. Les deux se
posent et se retirent par commande, jamais globalement.

⚠️ SonarQube était **arrêté** (`Exited (255)`, ~1 h) au pré-vol, vraisemblablement
emporté par l'arrêt du banc de charge de task-184. Relancé par
`docker start sonarqube_db sonarqube`.
