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

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] **Cause écrite pour chacune des trois familles** (`EnrichmentOperationScope`
      + `MailRepositoryEnrichPersistInstrumentation`, `SemanticSearchRepository`,
      `MarkdownPdfRenderer`), avec la mesure qui l'établit — ou, pour une
      famille dont la cause résiste, le constat explicite « cause non établie »
      plutôt qu'une hypothèse présentée comme un fait
- [ ] **Reproductibilité démontrée avant correctif** : pour au moins une
      famille, une commande qui fait échouer le test **à la demande** (l'échec
      observé au hasard ne prouve pas qu'on a compris)
- [ ] **10 exécutions complètes consécutives** de
      `dotnet test HealthPlatform.Api.Mail.sln`, **0 échec**, journal des 10
      exécutions consigné dans la task. C'est le seul critère qui distingue
      « corrigé » de « pas retombé cette fois »
- [ ] Aucun test désactivé, ignoré, exclu du CI ou mis sous `retry` — vérifiable
      par diff : le nombre de tests exécutés est ≥ celui d'avant (4101 au
      2026-09-06)
- [ ] Si le parallélisme est désactivé quelque part : un commentaire dans le
      `xunit.runner.json` concerné qui dit **pourquoi**, et la durée avant/après
      de la suite mesurée et consignée
- [ ] Garde-fou anti-récidive en place et **prouvé** par un cas de test qui
      échoue si on réintroduit le partage d'état incriminé
- [ ] CI `develop` verte après merge

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
| /develop | failed | 50 min 54 s | — | — | — | — |
| **Total cycle** | | **51 min 53 s** | **0 (0.0 s)** | **0 (0.0 s)** | **0 (0.0 s)** | |
