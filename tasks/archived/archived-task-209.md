# todo-task-209.md — Le dimensionnement des VUs suppose des latences que le banc ne produit plus

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: task-203 (qui a introduit le modèle), task-204 (l'escalier qui l'a mis en défaut)
**Priorité**: **1/6** — Instrument (ordre arrêté le 2026-07-31, objectif montée en charge)
> Le harnais produit des abandons qu'on impute a l'application : les 4 tirs du 2026-07-31 sont sortis INVALIDES a cause de lui. Rien ne se conclut tant que ce n'est pas corrige.

> **Origine** : escalier de capacité du 2026-07-29 (task-204). Deux campagnes ont
> été nécessaires — la première a été jetée — parce que le modèle de
> dimensionnement sous-provisionne les pools dès que la latence réelle s'écarte de
> ses constantes de référence.

## Objective

Que le harnais cesse de produire des abandons qu'on impute à l'application, et
qu'il **dise** quand son propre modèle est démenti par la mesure.

## Le défaut

`lib/vu-sizing.js` dimensionne chaque pool par la loi de Little à partir de
`REFERENCE_ITERATION_SECONDS`, constantes **mesurées le 2026-07-27**. Écart
constaté le 2026-07-29, même scénario, même population :

| Sous-scénario | Référence du modèle | Mesuré à 486 req/s | Mesuré à 972 req/s | Écart au pire |
|---|---|---|---|---|
| `read` (list + content) | **0,16 s** | 0,41 s | **1,65 s** | **×10** |
| `folders` | 0,06 s | 0,05 s | 0,17 s | ×2,8 |
| `search` | 0,33 s | 0,24 s | 0,66 s | ×2,0 |
| `send` | 1,30 s | 1,18 s | 1,70 s | ×1,3 |

Le facteur de queue (`DEFAULT_TAIL_FACTOR = 4`) est censé absorber la variance,
pas un facteur 10 sur la moyenne. Conséquences mesurées :

- **1re campagne** (`tailFactor` par défaut) : 4,6 % d'abandons **au premier
  palier**, dont 1 076 sur `folders` et 763 sur `read`. Campagne jetée.
- **2e campagne** (`VU_TAIL_FACTOR=8`) : paliers 486 et 630 valides (0,67 % et
  0,74 %), puis abandons croissants **concentrés sur `read`** (783 → 4 916 →
  9 960), jusqu'à 7,4 % au palier 972.

**La cause de l'écart est double, et l'ordre compte.** D'abord structurelle : les
constantes ont été mesurées avec des `read` servis **depuis la base** (après
enrichissement), alors qu'une campagne d'escalier **purge les tables entre
paliers** — condition nécessaire pour que les `enrich` ne court-circuitent pas.
`read` part donc sur IMAP, et rien dans le harnais ne dit que ces deux exigences
se contredisent.

Ensuite — et c'est ce qui interdit la correction naïve — **au-delà du genou la
latence n'est plus une propriété du scénario mais du serveur qui congestionne**.

> ### ⚠️ Élargir les pools AGGRAVE le tir — mesuré, ne pas re-débattre
>
> Expérience de discrimination du 2026-07-29, budget identique de 882 req/s, seul
> `VU_TAIL_FACTOR` change (8 → 16) :
>
> | | `tail=8` | `tail=16` |
> |---|---|---|
> | Débit délivré | 824,8 req/s | **716,4** (−13 %) |
> | Abandons | 4,21 % | **13,49 %** |
> | p95 | 1 309 ms | **6 766 ms** |
> | `read_list` moy | 714 ms | **3 606 ms** |
> | File ThreadPool par réplica | 136/93/13/10/7 | **406/951/579/648/813** |
>
> Plus de concurrence cliente → **moins** de débit. Au-delà du genou, agrandir le
> pool ne « libère » rien : il alimente une file bloquante côté serveur
> (task-205). Le harnais ne doit donc pas chercher à annuler les abandons par le
> dimensionnement — il doit **dire lequel des deux mécanismes** les produit.

⚠️ **Le piège est celui que task-203 a créé en le corrigeant** : un pool
sous-dimensionné produit « un tir invalide qui a l'air valide » — et ici, mieux : un
tir dont l'invalidité est **imputée à l'application** (« la charge nominale n'a
jamais été appliquée ») alors qu'elle vient du client. C'est la même erreur
d'attribution que task-204 combat, d'un cran en amont.

## Contenu attendu

1. **Fermer la boucle sur la mesure** : dimensionner sur une latence **observée**
   plutôt que sur une constante figée — au minimum une surcharge par variable
   d'environnement (`ITER_SECONDS_READ=…`) qui manque aujourd'hui, au mieux une
   phase d'échauffement courte qui mesure puis dimensionne.
2. **Rendre le démenti visible** : en fin de tir, comparer la latence réelle par
   sous-scénario à celle utilisée pour le plan et **écrire** l'écart. Un écart > 2×
   doit apparaître dans le rapport comme cause candidate des abandons, à côté du
   verdict de validité — pas à la place, mais jamais en silence.
3. **Rafraîchir les constantes** avec les mesures du 2026-07-29, en **nommant les
   conditions** de mesure (tables purgées ou non — c'est ce qui change tout pour
   `read`).
4. **Documenter la contradiction** purge / dimensionnement dans
   `docs/loadtest.md` et dans le skill `loadtest-skill`, avec la conduite à tenir.

## Hors scope

- Les règles de conclusion du rapport (task-208).
- Le facteur limitant applicatif (task-205) — c'est lui qui fait monter la latence
  réelle ; cette task ne corrige que la façon dont le harnais y réagit.

## Definition of Done

- [ ] Build passes (0 errors) — Tests pass (0 failures)
- [ ] Test unitaire : une surcharge de latence par sous-scénario est prise en
      compte par le plan (pool dimensionné en conséquence)
- [ ] Test unitaire : un écart > 2× entre latence planifiée et latence mesurée est
      **écrit** dans le rapport, avec le sous-scénario nommé
- [ ] Test unitaire : sur les données du palier 972 req/s de la campagne
      (`read` planifié à 0,16 s, mesuré à 1,65 s), le rapport nomme `read` comme
      cause candidate des 7,4 % d'abandons
- [ ] Les constantes de référence sont à jour et **leurs conditions de mesure sont
      écrites** dans le module
- [ ] **Le rapport DISTINGUE les deux causes d'abandon** — c'est le cœur de la
      task, et l'expérience ci-dessous interdit de se contenter d'élargir les
      pools : « pool client épuisé alors que le serveur répond dans les temps »
      (dimensionnement) vs « le serveur ralentit, la concurrence cliente
      s'accumule » (congestion serveur). Test unitaire sur les deux jeux de
      données de la campagne
- [ ] **Mesure au banc** : au palier 756 req/s, le rapport nomme laquelle des deux
      causes produit ses 1,15 % d'abandons, et l'argumente par un chiffre
      (latence planifiée vs mesurée, file ThreadPool serveur)
- [ ] `docs/loadtest.md` + `loadtest-skill` : la contradiction purge /
      dimensionnement est documentée

## Manual Test Plan

1. Sans banc : `tests/loadtest-k6/selftest.sh` (les nouveaux tests portent sur des
   fixtures, dont celles de la campagne du 2026-07-29).
   ⚠️ **`tests/loadtest-k6/reports/` est gitignoré** (`.gitignore:386`) : les JSON
   de la campagne n'existent que sur la machine de banc. Promouvoir en fixtures
   versionnées ceux dont la DOD a besoin — au minimum les paliers 882 et 972 req/s
   aux deux `VU_TAIL_FACTOR` (8 et 16), qui portent la comparaison
   « dimensionnement » vs « congestion serveur ».
2. Avec banc, pour la DOD de mesure : monter le banc, 200 praticiens re-câblés,
   purger les tables, puis
   ```bash
   BYPASS_KEY=loadtest-local-only USERS=200 MESSAGES_PER_USER=100 \
   SESSION_ROTATION=0.001 RPS=840 ENRICH_SHARE=0.05 \
     tests/loadtest-k6/run.sh mixed --env VUS=60 --env DURATION=3m
   ```
   sans forcer `VU_TAIL_FACTOR` : le plan doit se dimensionner seul et le tir sortir
   valide.
3. Lire la section « Validité du tir » et la nouvelle comparaison
   latence planifiée / latence mesurée.

## Branches

- `api-mail` (pushed) : `feat/task-209-vu-sizing-measured-latency` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-209-vu-sizing-measured-latency
- `dtos-mss` (pushed, auto-inclus) : `feat/task-209-vu-sizing-measured-latency` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-209-vu-sizing-measured-latency
  (aucun changement de contrat attendu — branche créée proactivement, pas de PR si aucun commit)

## Develop log

- **Repos touchés** : `api-mail` uniquement (harnais k6 : JS + Python + docs).
  `dtos-mss` : aucun commit, aucun contrat touché → pas de publication NuGet,
  pas de bump consommateur, pas de PR.
- **Commits** (`feat/task-209-vu-sizing-measured-latency`) :
  - `0285b6b` `feat(loadtest): dimensionner les VUs sur une latence observée, pas figée`
  - `ee99c6a` `feat(loadtest): le rapport distingue dimensionnement et congestion serveur`
  - `a46e984` `docs(loadtest): la contradiction purge / dimensionnement, et ses deux remèdes`
- **Build / tests** : `dotnet build` 0 erreur / 0 avertissement ;
  `dotnet test` **3 207 réussis, 0 échec** (16 ignorés — suite IA, `[SKIP]`
  d'origine). Auto-tests du harnais : `selftest.sh` vert — **15 tests node**
  (`lib/vu-sizing.test.mjs`, +4) et **77 tests Python** (+19 dans
  `test_report_sizing.py`).
- **Vérifié au vrai k6** (`k6 inspect`, v1.4.2, aucun banc requis) : au budget
  882 req/s le plan passe de 793 VUs forcés à `VU_TAIL_FACTOR=8` à **890 VUs au
  facteur par défaut** — les constantes rafraîchies remplacent le réglage manuel.
  `ITER_SECONDS_READ=1.65` ne redimensionne **que** `read` (pre 122 → 486), et
  `ITER_SECONDS_REDA=…` fait échouer le tir au lieu d'être ignoré.

### Ce qui a été livré, point par point du « Contenu attendu »

1. **Boucle fermée sur la mesure** — surcharge `ITER_SECONDS_{FOLDERS,READ,
   SEARCH,SEND,ENRICH}`, câblée de `config.js` jusqu'au plan, et le rapport
   **imprime la ligne à recopier** (`ITER_SECONDS_READ=0.41 …`). La phase
   d'échauffement auto-mesurante (le « au mieux » de l'US) n'est pas livrée :
   le minimum explicitement admis l'est, et l'écart est désormais visible, ce
   qui rend l'échauffement automatisable plus tard sans deviner.
2. **Démenti visible** — section « Latence planifiée vs mesurée », écart par
   sous-scénario, seuil ×2, renvoi depuis le verdict de validité.
3. **Constantes rafraîchies** — palier 486 req/s du 2026-07-29, **base purgée,
   sous le genou**, avec `REFERENCE_MEASURED_AT` / `REFERENCE_CONDITIONS`
   recopiés dans le contexte de chaque tir archivé. Délibérément **pas** les
   valeurs d'un palier haut : dimensionner sur la congestion l'alimenterait.
4. **Contradiction documentée** — `docs/loadtest.md` §4a-bis, `README.md`
   piège n°6, `loadtest-skill` (étape 4), chacun avec la table « quelle cause →
   quelle conduite ».

### Un bug trouvé en chemin, hors énoncé

`iterationSecondsFor(key, overrides)` **remplaçait** la table de référence au
lieu de la fusionner : poser une seule surcharge renvoyait tous les autres
sous-scénarios sur le repli pessimiste d'une seconde, soit des pools 4 à 20 fois
trop larges. La surcharge demandée par l'US aurait donc été inutilisable telle
quelle. Corrigé et couvert par un test.

### ⚠️ Réserve honnête sur les fixtures — à lire avant `/review`

Le Manual Test Plan demandait de « promouvoir en fixtures versionnées » les JSON
de la campagne du 2026-07-29. **Ils n'existent plus sur cette machine** :
`tests/loadtest-k6/reports/` est gitignoré et n'y contient plus que
`2026-07-25/`, `2026-07-26/`, `2026-07-27/` — ni la campagne du 29, ni les tirs
du 31. Ils n'ont donc pas pu être promus.

Les cinq fixtures `k6-campagne-*.json` / `prom-campagne-2026-07-29.json` sont
**reconstruites depuis les chiffres publiés** (`archived-task-205.md`,
`reports/INDEX.md`, `todo-task-209.md`), et chacune porte sa provenance dans une
clé `_provenance`. Trois garde-fous :

- un test dédié (`FixtureIntegrityTests`) vérifie qu'elles **reproduisent les
  chiffres publiés** — abandons 4,21 / 13,49 / 7,38 %, débits plateau 824,8 /
  716,4 / 857,9 req/s, `read_list` 714 / 3 606 / 1 533 ms — avant que les tests
  d'attribution ne s'y fient ;
- les assertions ne portent **que** sur des grandeurs publiées ;
- les opérations non publiées à 882 req/s reprennent leurs valeurs du palier 486,
  ce qui **sous-estime** leur dégradation : une fixture de remplissage ne peut
  donc pas fabriquer un écart qui n'existait pas.

Si le humain retrouve les JSON d'origine (sauvegarde, autre poste), les
remplacer est un geste sans risque : les tests échoueraient si les chiffres
divergeaient. Même réserve pour task-208, qui demande les mêmes fichiers.

### ⚠️ DOD non atteint : la mesure au banc

- [ ] « **Mesure au banc** : au palier 756 req/s, le rapport nomme laquelle des
      deux causes produit ses 1,15 % d'abandons » — **non fait**. Le banc n'est
      pas monté (ni AppHost, ni Dovecot/GreenMail/Toxiproxy) et le monter suppose
      seed de 200 praticiens × 100 messages, purge, tir de 3 min et démontage
      obligatoire. C'est l'**étape 2 du Manual Test Plan**, côté humain — comme
      l'a été le « Tir de vérification log » de task-205. Commande exacte :

      ```bash
      BYPASS_KEY=loadtest-local-only USERS=200 MESSAGES_PER_USER=100 \
      SESSION_ROTATION=0.001 RPS=840 ENRICH_SHARE=0.05 \
        tests/loadtest-k6/run.sh mixed --env VUS=60 --env DURATION=3m
      ```

      sans forcer `VU_TAIL_FACTOR` : le plan doit se dimensionner seul. Lire
      ensuite la section « Latence planifiée vs mesurée » du rapport.

Tous les autres critères de la DOD sont couverts par les auto-tests.

- **Étape suivante** : `/forge-simplify task-209`.

## Simplify log

- **Repos passés** : `api-mail` (seul repo touché).
- **Appliqué & committé** : `api-mail` — 2 fichiers, `68a4e47`
  `refactor(loadtest): simplify pass (/simplify) — task-209`.
- **Aucun changement** : —
- **Rollback (validation RED)** : aucun.
- **Skippés (contrat / exclus)** : `dtos-mss` (porteur de contrat, et sans
  diff de toute façon), `interop-cda`, `devops`, `psc-proxy-*`.
- **Build / tests** : `dotnet build` 0 erreur / 0 avertissement ;
  `selftest.sh` vert (15 node + 77 Python) ; `k6 inspect` re-vérifié — la
  surcharge `ITER_SECONDS_READ=1.65` ne redimensionne toujours que `read`.

Six nettoyages, tous sur l'axe **reuse** et **simplification** :

| Nettoyage | Ce que la duplication coûtait |
|---|---|
| `dropped_by_scenario` + `is_rate_free` partagés par la garde de validité et l'attribution | deux filtres « scénario sans débit imposé » qui auraient dérivé au premier `shared-iterations` ajouté — garde et verdict cessant de parler du même chiffre |
| `worst_threadpool_queue`, `worst_server_p95_ms` extraits | trois chemins différents pour lire les deux mêmes séries Prometheus |
| `pinned_candidates` utilise `THREADPOOL_QUEUE_CONGESTED` | un `100` en dur face au seuil nommé du verdict : le rapport pouvait épingler la file ThreadPool **et** imputer les abandons au harnais |
| `drop_attribution` reçoit le verdict déjà calculé | `validity()` dérivé deux fois par rapport — deux occasions de publier deux taux d'abandons dans le même document |
| deux branches identiques fusionnées | arbre de décision de la cause plus court d'un cas |
| `overrideFor` partagé côté JS | `iterationSecondsFor` testait le type strictement, `iterationSecondsSource` par coercition : le plan pouvait déclarer `override` en utilisant la référence |

- **Étape suivante** : `/sonar task-209` (api-mail touché).

## Sonar log

- **Phase 1 (new code)** : 11 issues fixées + 2 hotspots revus. Il reste
  **3 findings**, tous **antérieurs à cette task** — provenance ci-dessous.
- **Phase 2 (legacy)** : 1 itération. 1 issue fixée (`csharpsquid:S1144`).
- **Build / tests** : ✓ `dotnet build` Release 0 erreur ; 5 projets de tests
  verts ; `selftest.sh` du harnais vert (15 node + 77 Python).
- **Analyses** : 3 (scan initial → fixes → vérification).

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate | ERROR | ERROR | → (voir « ce qui reste ») |
| `new_violations` | 14 | **3** | **−11** |
| **Bugs** | **1** | **0** | **−1** |
| Vulnerabilities | 0 | 0 | = |
| Security hotspots à revoir | 2 | **0** | **−2** (100 % revus) |
| Code smells | 13 | **3** | **−10** |
| Coverage (projet) | 86,6 % | 86,5 % | −0,1 pt |
| New coverage | 86,2 % | 86,1 % | −0,1 pt (seuil 80 % ✓) |
| Duplication | 0,6 % | 0,6 % | = |
| **Reliability** | **C** | **A** | **↑ 2 crans** |
| Security | A | A | = |
| Maintainability | A | A | = |

> ⚠️ **La « baseline » est celle du premier scan de cette branche, pas celle
> qu'affichait le serveur.** Le dernier scan archivé datait d'avant plusieurs
> tasks mergées — ses numéros de ligne ne correspondaient même plus au
> `report.py` de `develop`. Comparer à lui aurait produit un Δ inventé.

### Ce qui a été corrigé, et ce qui ne l'est pas

| Finding | Provenance | Traitement |
|---|---|---|
| `python:S1764` (**BUG**) — `value == value` | task-204 | fixé (`math.isnan`) — **c'est ce seul finding qui tenait `reliability_rating` à C** |
| `javascript:S1940` ×3 | 1 task-209, 2 task-203 | fixé — mais **pas** comme Sonar le suggère (voir ci-dessous) |
| `python:S1192` ×2 littéraux (7 occ.) | task-198/204, +1 occ. task-209 | fixé (constantes `P95`, `UTC_OFFSET`/`UTC_SUFFIX`) |
| `python:S5713` ×2 | task-204 | fixé (`URLError` ⊂ `OSError`, `JSONDecodeError` ⊂ `ValueError`) |
| `python:S1481` ×2 | **task-209** | fixé (`_, _, telemetry = …`) |
| `csharpsquid:S1144` — champ mort | task-205 | fixé, vérifié sans usage dans `src/` et `tests/` |
| hotspot `python:S5332` (URL `http://`) | **task-209** | `SAFE` — URL de fixture, le test ne fait aucun appel réseau |
| hotspot `python:S5852` (regex) | task-204 | `SAFE` — entrée produite par le harnais, jamais par un tiers |
| `python:S3776` ×3 | **task-204** (`git blame` → `c10fa7b`, PR #130) | **accepté** (Phase 2 best-effort) |

**Pourquoi les 3 `S3776` restent** — ils portent sur `budget_rows`,
`reduce_prom_matrix` et `_observe_table`, tous hors du diff de cette task. Et
`budget_rows` est **exactement la fonction que task-208 doit réécrire** (son
DOD : « Débit demandé vs délivré calculé sur le plateau ») : la refactorer ici
créerait une collision avec la task suivante du même EPIC. Le Quality Gate
reste donc ERROR sur `new_violations = 3`, **sans dette introduite par
task-209**.

### ⚠️ Un fix Sonar qu'il ne fallait pas appliquer tel quel

`javascript:S1940` propose de remplacer `!(x > 0)` par `x <= 0`. **Ce n'est pas
équivalent** : toute comparaison avec `NaN` est fausse, donc `!(NaN > 0)` vaut
`true` là où `NaN <= 0` vaut `false`. Appliqué littéralement, le « fix » aurait
supprimé la garde qui fait échouer un tir sur `ITER_SECONDS_READ=vite` — c'est-
à-dire le silence que cette task existe précisément pour empêcher. Écrit
`Number.isFinite(x) && x > 0` : la règle est satisfaite **et** le cas NaN reste
couvert. Consigné dans `conventions/javascript.md`.

### Conventions alimentées (boucle d'auto-amélioration)

- `conventions/javascript.md` — nouvelle entrée `javascript:S1940` (le piège NaN).
- **`conventions/python.md` — fichier créé.** Il manquait alors que l'analyse
  d'`api-mail` est multi-langage et que le moteur de rapport du banc est en
  Python. Six entrées (`S1192`, `S1764`, `S5713`, `S1481`, `S5332`/`S5852`,
  `S3776`). Directement utile à task-208, qui va réécrire `report.py`.
- `conventions/csharp.md` — la note de portée pointe désormais aussi vers
  `python.md`.

### Anomalie d'outillage à corriger (hors périmètre de cette task)

`agents/sonar.md` affirme que l'instance est en **9.9.8** et impose
`/d:sonar.login`. Le serveur est en **25.6.0**, où la propriété est
`sonar.token`. J'ai utilisé `sonar.token` — les trois analyses ont réussi. En
suivant l'agent à la lettre, un futur run perdrait ~6 min (build + tests
complets) avant de voir échouer le `end` sur une erreur d'authentification
trompeuse. L'encadré ⚠️ de `agents/sonar.md` mérite d'être inversé.

- **Étape suivante** : `/review task-209` — `client-angular` et `client-mobile`
  ne sont pas dans `**Repos**:`, donc `/lint-angular`, `/lint-mobile` et
  `/verify-visual` skippent proprement.

## PRs

- `api-mail` : **https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/132**
  — label `awaiting-human-merge`, `MERGEABLE`, 8 commits, 15 fichiers.
- `dtos-mss` : **aucune PR** — la branche existe (créée proactivement par
  `/start`) mais n'a aucun commit : la task ne touche aucun contrat.
- `client-angular`, `client-mobile` : hors `**Repos**:` — non touchés,
  `/lint-angular`, `/lint-mobile` et `/verify-visual` ont skippé proprement.

## Code Review Summary

Verdict : **APPROVED** — 9 fichiers de code relus, 0 blocage, 1 correction
appliquée pendant la revue.

| Fichier | Verdict |
|---|---|
| `lib/vu-sizing.js` | ✅ module pur, surcharge fusionnée, gardes NaN explicites |
| `lib/config.js` | ✅ parsing délégué au module pur (testable), lève sur variable inconnue |
| `scenarios/mixed.js` | ✅ simple adaptateur, déclare la provenance de chaque latence |
| `report.py` | ✅ sections pures, testées sur fixtures, aucun I/O ajouté |
| `test_report_sizing.py` | ✅ 19 tests, assertions sur grandeurs publiées uniquement |
| `lib/vu-sizing.test.mjs` | ✅ +4 tests, dont la non-régression de la surcharge ciblée |
| `src/Application/Helpers/SafeCacheExtensions.cs` | ✅ champ mort retiré, vérifié sans usage |
| `docs/loadtest.md`, `README.md` | ✅ la contradiction est nommée, avec la conduite à tenir |

**Correction issue de la revue** (`23d6b03`) : `ITER_SECONDS_*` n'agit que sur
`mixed` — les scénarios mono gardent leur pool de convenance `4 × VUS`. Poser
la variable sur `run.sh read` était un **no-op silencieux**, soit exactement le
mode d'échec que cette task combat. Documenté.

**Validation**

| Contrôle | Résultat |
|---|---|
| `dotnet build` Release | ✓ 0 erreur, 0 avertissement |
| `dotnet test` Release | 3 206 réussis, 16 ignorés, **1 échec pré-existant** (voir ci-dessous) |
| `selftest.sh` (harnais) | ✓ 15 tests node + 77 tests Python |
| `k6 inspect` sur `mixed.js` | ✓ plan construit, surcharge ciblée vérifiée |
| Sync `develop` | ✓ 0 commit de retard, aucun merge nécessaire |

**L'échec de test est pré-existant et sans lien** :
`MailExportServiceTests.BuildPdfWithMedicalDocumentHtmlBodyFallback`, l'un des
flaky documentés du repo. Il passe **3/3 en isolation** et n'échoue qu'en suite
complète Release. Le seul fichier `src/` du diff est `SafeCacheExtensions.cs`,
que `MailExportService` n'utilise pas — vérifié.

## Reste à faire par le humain

1. **Tester la US de bout en bout** (Manual Test Plan recopié dans la PR), dont
   la **DOD de mesure au banc au palier 756 req/s** — non faite par la forge.
2. **Merger la PR #132** — HAG, règle 10.
3. Hors périmètre, mais relevé pendant le cycle :
   - `agents/sonar.md` annonce une instance SonarQube **9.9.8** et impose
     `sonar.login`. Le serveur est en **25.6.0**, où la propriété est
     `sonar.token`. Un run suivant l'agent à la lettre perdrait ~6 min avant
     d'échouer sur une erreur d'authentification trompeuse.
   - Les JSON de la campagne du 2026-07-29 ont disparu de `reports/`.
     **Task-208 en a besoin** et butera sur le même manque.

## Merged

- **Date** : 2026-07-31
- `api-mail` : squash `7e4b322` — PR
  [#132](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/132)
  fermée. Ref distant `feat/task-209-vu-sizing-measured-latency` supprimé,
  **branche locale conservée**.
- `dtos-mss` : aucune PR (branche sans commit, aucun contrat touché) — ref
  distant supprimé, repo repassé sur `develop`.
- `client-angular`, `client-mobile`, `devops`, `psc-proxy-*` : hors périmètre.
- **Staging** : aucune branche `forge/staging-*` — task lancée par `/start`
  isolé, pas par un run `/forge`.
- **CI `develop`** :
  https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/30661717916
