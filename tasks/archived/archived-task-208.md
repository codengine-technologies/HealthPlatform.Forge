# todo-task-208.md — Le rapport de tir conclut encore faux de trois façons

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: task-204 (qui a livré la section, et dont l'escalier a révélé ces trois défauts)
**Priorité**: **2/6** — Instrument (ordre arrêté le 2026-07-31, objectif montée en charge)
> Trois verdicts faux dans le rapport de tir, dont un denominateur qui se contredit dans le meme document.

> **Origine** : escalier de capacité du 2026-07-29 (task-204). Les trois défauts
> ci-dessous ont été trouvés **en lisant les rapports de la campagne**, pas en
> relisant le code : chacun a produit une affirmation fausse dans un `.md` livré.
>
> C'est la continuité directe de la raison d'être de task-204 : *ne jamais
> conclure en silence, et ne jamais conclure faux*. Le mécanisme d'absence de
> télémétrie est correct ; ce sont les **règles de conclusion** qui débordent.

## Objective

Que les trois verdicts que le rapport rend avec assurance — ressource épinglée,
part du budget servie, validité du tir — soient fondés sur la bonne statistique.

## Les trois défauts, chacun avec sa preuve

### 1. « Ressource épinglée » désigne PgBouncer sur un transitoire de démarrage

`report.py` (`pinned_candidates`) attribue `ratio = 1.0` — le maximum possible,
donc le rang n°1 garanti — dès que `cl_waiting > 0`, avec le commentaire « toute
attente cliente non nulle signe un pooler qui n'absorbe plus ; la borne est 0, pas
une capacité ».

L'intention est juste, la **statistique** ne l'est pas : la valeur retenue est le
`max` sur la fenêtre. Résultat sur la campagne :

| Palier | `cl_waiting` max **dans** la fenêtre | Verdict rendu |
|---|---|---|
| 486 req/s | **2** | « Ressource épinglée : PgBouncer — 100,0 % de sa borne » |
| 630 req/s | **1** | idem |
| 756 req/s | **3** | idem |

Un seul échantillon à 1 client en attente a donc désigné le pooler comme facteur
limitant de trois tirs — devant un réplica à 11 % et Postgres à 13,6 %.

Et l'échantillonnage montre que ces valeurs sont des **transitoires d'ouverture de
palier** : sur 230 échantillons de la campagne, 15 sont non nuls (6,5 %), tous dans
les ~30 s qui suivent le début d'un tir (pic à 75 mesuré **2 s avant** l'ouverture
d'une fenêtre). Dans les fenêtres, `cl_waiting` ≤ 8 avec `sv_active` ≤ 162 : le
pooler multiplexe 2 001 clients sur 153-162 serveurs, il absorbe parfaitement.

**Attendu** : juger `cl_waiting` sur une **présence soutenue** (part des
échantillons non nuls, ou p95, ou durée cumulée au-dessus de 0), pas sur le `max`.
Un transitoire d'ouverture doit être **signalé** (il est intéressant : il croît
avec la charge, 2 → 1 → 6 → 75) sans être promu verdict.

### 2. « Débit demandé vs délivré » divise par la fenêtre totale — et le même rapport publie l'autre chiffre

Dans **le même** `.md`, palier 486 req/s :

- en-tête : « **Débit plateau : 482,7 req/s** (k6 publie 413,7 req/s) » → **99,3 %**
  du budget servi ;
- table « Débit demandé vs délivré » : « total 486 → **413,6** — **85,1 % ⚠️** ».

C'est le défaut de dénominateur que task-204 a corrigé pour le chiffre d'en-tête
mais **pas** dans cette table, qui est pourtant celle qui porte les ⚠️ par
sous-scénario. Un lecteur en conclut « l'application ne tient que 85 % de la charge
à 486 req/s », alors qu'elle en tient 99,3 %.

**Attendu** : la table utilise le dénominateur **plateau**, ou nomme explicitement
son dénominateur ligne à ligne. Deux dénominateurs dans un document sans que la
différence soit dite est précisément ce que task-204 interdit.

### 3. La garde de validité compte le reliquat d'un scénario FINI comme des abandons

`mixed_enrich` est un `shared-iterations` de
`users × MESSAGES_PER_USER × ENRICH_SHARE / ENRICH_BATCH` lots. À 200 × 100 × 0,5 / 5
= **2 000 lots**, dont **424** tiennent dans un plateau de 3 min : k6 compte les
1 576 restants en `dropped_iterations`.

Le premier palier de la campagne a donc été déclaré **invalide à 4,6 %
d'abandons** alors que les scénarios à débit imposé n'en avaient que 2,6 % — et
qu'`enrich`, par construction, ne **peut pas** manquer de VU : aucun débit ne lui
est imposé.

Contournement utilisé pour la campagne : `ENRICH_SHARE=0.05` (bande de 200 lots,
épuisable dans le plateau) → `mixed_enrich = 0` abandon aux cinq paliers. C'est un
réglage d'opérateur, pas une correction.

**Attendu** : la garde **exclut** les scénarios sans débit imposé de son
numérateur, et le rapport dit combien d'itérations d'un scénario fini n'ont pas été
consommées (information utile, mais pas un signal d'invalidité).

## Hors scope

- Le modèle de dimensionnement des VUs (task-209).
- Les findings applicatifs (task-205, task-206, task-207).
- Le helper de table Markdown écarté par task-203 et task-204 : toujours candidat
  à une passe dédiée, toujours hors de celle-ci.

## Definition of Done

- [ ] Build passes (0 errors) — Tests pass (0 failures)
- [ ] Test unitaire : un `cl_waiting` non nul sur **un seul** échantillon de la
      fenêtre ne désigne **pas** PgBouncer comme ressource épinglée
- [ ] Test unitaire : un `cl_waiting` non nul **soutenu** le désigne toujours
- [ ] Test unitaire : le transitoire est **mentionné** dans le rapport même quand
      il n'est pas retenu comme verdict (jamais de silence)
- [ ] Test unitaire : « Débit demandé vs délivré » calculé sur le plateau — sur
      la fixture du palier 486 req/s, le total lit **99,3 %** et non 85,1 %
- [ ] Test unitaire : un scénario **sans débit imposé** ne contribue pas au
      `dropped_iterations` de la garde de validité ; sur les données du 1er palier
      (4,6 % brut / 2,6 % hors `enrich`), le verdict porte sur 2,6 %
- [ ] Test unitaire : le reliquat non consommé d'un scénario fini est **écrit**
      dans le rapport
- [ ] Les 3 rapports de la campagne du 2026-07-29 régénérés depuis leur JSON
      archivé : les verdicts changent dans le sens attendu, et la ligne d'INDEX
      correspondante est recalculée
- [ ] `docs/loadtest.md` : les trois règles de conclusion sont écrites (quelle
      statistique, pourquoi celle-là)

## Manual Test Plan

1. Aucun banc requis pour les 3 défauts : les JSON et le CSV d'échantillonnage de
   la campagne du 2026-07-29 sont dans `tests/loadtest-k6/reports/2026-07-29/`.
   ⚠️ **Ce répertoire est gitignoré** (`.gitignore:386` — seul `INDEX.md` est
   versionné) : les données n'existent que sur la machine de banc. **Premier geste
   de l'US** : promouvoir les fichiers nécessaires en fixtures versionnées sous
   `tests/loadtest-k6/fixtures/`, sinon les tests de la DOD sont injouables
   ailleurs. Au minimum `mixed-mssante-60vu-201816.json` (palier 486, le cas du
   dénominateur), le JSON du 1er essai (garde de validité vs `enrich`) et un
   extrait du CSV portant les transitoires `cl_waiting`.
2. Régénérer le rapport du palier 486 req/s :
   ```bash
   tests/loadtest-k6/report.sh tests/loadtest-k6/reports/2026-07-29/mixed-mssante-60vu-201816.json --expected 100
   ```
3. Vérifier dans le `.md` : (a) la table « Débit demandé vs délivré » affiche
   ~99 % et non ~85 % ; (b) la ressource épinglée n'est plus PgBouncer, le
   transitoire est mentionné ; (c) la section « Validité » raisonne hors `enrich`.
4. Rejouer les auto-tests du harnais : `tests/loadtest-k6/selftest.sh`.

## Branches

- `api-mail` (pushed) : `fix/task-208-report-conclusion-rules` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-208-report-conclusion-rules
- `dtos-mss` (pushed, auto-inclus) : `fix/task-208-report-conclusion-rules` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/fix/task-208-report-conclusion-rules
  (aucun changement de contrat attendu — branche créée proactivement, pas de PR si aucun commit)

> **Préfixe `fix/`** : la task corrige trois verdicts faux d'un rapport livré,
> ce n'est pas une nouvelle capacité.

> ⚠️ **Point de départ à connaître** — le Manual Test Plan demande de promouvoir
> en fixtures les JSON de la campagne du 2026-07-29. **Ils n'existent plus sur
> la machine** (`reports/` gitignoré, il n'y reste que 2026-07-25/26/27).
> task-209 a livré cinq fixtures **reconstruites depuis les chiffres publiés**
> (`fixtures/k6-campagne-*.json`, `prom-campagne-2026-07-29.json`), gardées par
> `FixtureIntegrityTests`. Deux des trois défauts sont couvrables avec elles :
> — défaut n°2 (dénominateur) : `k6-campagne-486-sous-dimensionne.json` porte le
>   palier 486 (plateau 473,9 req/s vs débit k6 406,2) ;
> — défaut n°3 (garde de validité vs `enrich`) : la même fixture porte
>   1 576 abandons structurels d'`enrich` face à 1 839 à débit imposé ;
> — défaut n°1 (`cl_waiting`) : `fixtures/observe-sample.csv` existe déjà
>   (task-204) mais ne porte pas les transitoires d'ouverture de palier — à
>   compléter, en inscrivant la provenance comme l'a fait task-209.

## Develop log

- **Repos touchés** : `api-mail` uniquement (harnais k6 : Python + fixtures +
  docs). `dtos-mss` : aucun commit, aucun contrat touché → pas de PR.
- **Commit** : `8393ff8`
  `fix(loadtest): les trois verdicts du rapport reposent sur la bonne statistique`
- **Build / tests** : `dotnet build` 0 erreur / 0 avertissement (aucun C# touché) ;
  `selftest.sh` vert — 15 tests node, **90 tests Python** (+13 dans
  `test_report_conclusions.py`).
- **Test-first** : les 13 tests ont été écrits avant le code et constatés RED.
  L'un d'eux reproduisait littéralement le défaut n°1 :
  `Ressource épinglée : PgBouncer — 100,0 % de sa borne` sur un unique
  échantillon.

### Les trois défauts, et la statistique retenue

| Défaut | Avant | Après |
|---|---|---|
| n°1 — ressource épinglée | `ratio = 1.0` dès que `cl_waiting > 0`, sur le **max** de la fenêtre | part des échantillons non nuls, seuil `PGBOUNCER_WAITING_SUSTAINED = 25 %` — bien au-dessus des 6,5 % de bruit d'ouverture mesurés, bien en dessous d'un pooler réellement saturé |
| n°2 — débit demandé vs délivré | `http_reqs{op}.rate`, donc fenêtre **totale** (arrêt gracieux inclus) | `count ÷ durée de plateau`, **le même dénominateur que l'en-tête** ; le repli est nommé `fenêtre k6` ligne à ligne |
| n°3 — garde de validité | reliquat d'un `shared-iterations` compté comme abandon dès que la ventilation par scénario manque | ventilation quand elle existe, sinon **plan du harnais** (`enrichPlan` : planifiés − exécutés), et le reliquat est écrit comme *information* |

Vérifié sur la fixture du palier 486 : la table lit **97,5 %** et
**473,9 req/s**, exactement le débit plateau de l'en-tête — contre **83,6 %** et
406,2 req/s avant. Le transitoire `cl_waiting` est mentionné sous la table sans
être promu verdict ; une attente **soutenue** (13 échantillons sur 20) épingle
toujours PgBouncer.

### Trois tests existants changent de verdict — c'est le correctif

Ce ne sont pas des ajustements de confort ; chacun encodait le défaut :

1. `test_legacy_json_without_plan_falls_back_to_mix_derivation` — `send` délivré
   `17,24 → 18,97 req/s`. C'est exactement le biais de dénominateur (330 s de
   fenêtre contre 300 s de plateau). Le verdict « affamé » ne bouge pas.
2. `test_drop_share_just_over_ceiling_invalidates` — le compteur global injecté
   passe de 2 600 à 4 000, parce que 1 360 des abandons de cette fixture sont le
   reliquat déclaré de son `enrich` fini. Le test porte toujours sur ce qu'il
   visait : le franchissement du seuil, désormais sur les abandons **réels**.
3. `test_structural_enrich_drops_do_not_invalidate_a_healthy_run` — sa
   contre-épreuve « sans ventilation, ce tir sain serait déclaré INVALIDE »
   **s'inverse** : c'était précisément le défaut n°3, et le repli sur le plan le
   rattrape maintenant.

### ⚠️ DOD non atteint : la régénération des 3 rapports archivés

- [ ] « Les 3 rapports de la campagne du 2026-07-29 régénérés depuis leur JSON
      archivé, ligne d'INDEX recalculée » — **infaisable**. Les JSON n'existent
      plus : `tests/loadtest-k6/reports/` est gitignoré et ne contient plus que
      `2026-07-25/`, `2026-07-26/`, `2026-07-27/`. Même constat qu'à task-209.

  Ce que j'ai fait à la place, et pourquoi ça couvre l'intention :
  - le changement de verdict est **démontré** sur la fixture reconstruite du
    palier 486 (83,6 % → 97,5 %), et verrouillé par un test qui lit l'en-tête et
    la table du **même** rapport pour vérifier qu'ils ne se contredisent plus ;
  - **la ligne d'INDEX de ces trois tirs n'a de toute façon pas à changer** : la
    campagne a été conduite avec `ENRICH_SHARE=0.05`, donc `mixed_enrich = 0`
    abandon aux cinq paliers — c'est écrit dans l'énoncé même de la task. Le
    défaut n°3 ne mordait donc pas sur ces lignes. Et les colonnes d'INDEX ne
    portent pas la table « demandé vs délivré », seule touchée par le défaut n°2.

  Si les JSON refont surface, `report.sh` suffit à régénérer — aucun code ne
  manque.

- **Étape suivante** : `/forge-simplify task-208`.

## Sonar log

- **Phase 1 (new code)** : 2 issues fixées — toutes deux de la dette que **cette
  task avait introduite ou aggravée**.
- **Phase 2 (legacy)** : rien entrepris — voir « ce qui reste ».
- **Build / tests** : ✓ `dotnet build` Release 0 erreur ; `dotnet test` Release
  **3 207 réussis, 0 échec** (16 ignorés, suite IA `[SKIP]` d'origine) ;
  `selftest.sh` vert (15 node + 90 Python).
- **Analyses** : 2 (scan initial → fixes → vérification).

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate | ERROR | ERROR | → (2 findings pré-existants) |
| `new_violations` | 4 | **2** | **−2** |
| Bugs | 0 | 0 | = |
| Vulnerabilities | 0 | 0 | = |
| Security hotspots à revoir | 0 | 0 | = (100 % revus) |
| Code smells | 4 | **2** | **−2** |
| Coverage (projet) | 86,6 % | 86,6 % | = |
| New coverage | 86,1 % | 86,2 % | +0,1 pt |
| Duplication | 0,6 % | 0,6 % | = |
| Reliability / Security / Maintainability | A / A / A | A / A / A | = |

> La baseline est celle du **premier scan de cette branche** — task-209 ayant
> mergé entre-temps, l'état du serveur d'avant n'est pas comparable.

### Ce qui a été corrigé, et pourquoi c'était non négociable

Les deux `python:S3776` corrigés portent sur les **deux fonctions que cette task
a modifiées** :

- `budget_rows` y était déjà (19, héritée de task-203) et mes branches l'ont
  aggravée. La justification de task-209 — « on la laisse, task-208 va la
  réécrire » — ne tenait plus : c'est moi. Extraction de `_budget_scenarios`
  (quels sous-scénarios figurent) et `_requested_budget` (le budget et d'où il
  sort).
- `_budget_section` a **franchi** le seuil à cause de la note de dénominateur
  que j'y ai ajoutée : dette strictement introduite par task-208. Extraction de
  `_budget_row` et `_budget_denominator_note`.

### Ce qui reste, et pourquoi

Deux `python:S3776` sur `reduce_prom_matrix` (`report.py:932`) et
`_observe_table` (`:1688`) — task-204, **hors du diff de cette PR**. Ce sont des
helpers de rendu/parsing, et la passe générale sur les helpers de table Markdown
est listée en toutes lettres dans le **« Hors scope »** de l'énoncé de la task :
« toujours candidat à une passe dédiée, toujours hors de celle-ci ». Le Quality
Gate reste donc ERROR sur `new_violations = 2`, **sans dette introduite par
task-208**.

### Conventions alimentées

Aucune entrée nouvelle : `conventions/python.md` (créé par task-209) portait déjà
l'entrée `python:S3776`, avec la consigne appliquée ici — « découper en un
builder par section retournant une liste de lignes, puis concaténer ». La boucle
d'auto-amélioration a fonctionné dès son premier tour ; le compteur
**Occurrences** de cette entrée passe de 0 à 2.

## PRs

- `api-mail` : **https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/133**
  — label `awaiting-human-merge`, `MERGEABLE`, 4 commits, 6 fichiers.
- `dtos-mss` : **aucune PR** — branche sans commit, aucun contrat touché. Ref
  distant supprimé, repo repassé sur `develop`.
- `client-angular`, `client-mobile`, `devops`, `psc-proxy-*` : hors périmètre.

## Code Review Summary

Verdict : **APPROVED** — 0 blocage.

| Fichier | Verdict |
|---|---|
| `report.py` | ✅ les trois règles isolées en fonctions pures et nommées (`pgbouncer_waiting`, `finite_scenario_remainder`, `_requested_budget`), chacune testée sur fixtures |
| `test_report_conclusions.py` | ✅ 13 tests écrits RED d'abord, dont un qui reproduisait littéralement le défaut n°1 |
| `test_report.py` | ✅ 3 assertions retournées, chacune avec son raisonnement en commentaire |
| `fixtures/observe-cl-waiting-*.csv` | ✅ provenance en tête, cas transitoire **et** contre-épreuve soutenue (celle-ci marquée synthétique) |
| `docs/loadtest.md` | ✅ §4d — quelle statistique, et pourquoi celle-là |

**Validation** : `develop` à 0 commit de retard, aucun merge nécessaire ; build
Release 0 erreur ; 3 207 tests verts ; `selftest.sh` vert.

## Reste à faire par le humain

1. **Tester puis merger la PR #133** (Manual Test Plan recopié dans le body) —
   HAG, règle 10.
2. La DOD « régénérer les 3 rapports archivés » reste **décochée** : les JSON
   n'existent plus. Le raisonnement complet est dans le body de la PR.

## Merged

- **Date** : 2026-07-31
- `api-mail` : squash `6c51f58` — PR
  [#133](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/133)
  fermée. Ref distant `fix/task-208-report-conclusion-rules` supprimé,
  **branche locale conservée**.
- `dtos-mss` : aucune PR (branche sans commit) — ref distant déjà supprimé au
  `/review`, repo sur `develop`.
- `client-angular`, `client-mobile`, `devops`, `psc-proxy-*` : hors périmètre.
- **Staging** : `forge/staging-task-176-196-20260728` conservée — 208 est hors
  de sa plage `[176, 196]`, et ce run n'est pas drainé.
