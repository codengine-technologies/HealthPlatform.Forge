# todo-task-428.md — Tableau de bord « Consommation IA » : un panneau sans donnée ne se lit plus jamais « zéro »

**Repos**: api-mail
**Dependencies**: — (aucune)
**Epic**: E015
**Single frontend**: true
**Priorité**: **2**. Le test qui garde cette règle est rouge sur `develop` depuis le merge de task-385
(2026-10-21) sans que personne ne le voie, et ce tableau de bord est livré pour l'**import en production**. Un
panneau vide, ou un zéro fabriqué, s'y lit « aucune consommation » ou « aucun appel sans usage déclaré ». Correctif
petit, aucun comportement de l'API ne change.

> **Origine.** Constaté pendant task-424 (2026-11-06) : `tests/loadtest-k6/selftest.sh` est rouge sur `develop`, et
> le seul échec est `test_dashboards.DashboardNoDataTests.test_every_queried_panel_says_when_it_has_no_data`.

## Ce qui est établi

Fichier : `Api/Mail/src/AppHost/grafana/dashboards/mssante-ai-consumption.json` (task-385). Sur 12 panneaux qui
interrogent Prometheus :

- **8 panneaux n'ont pas de `noValue`**. Sans donnée, ils restent vides, et un panneau vide se lit « rien à
  signaler » (défaut 2 de task-224) :
  - « Tokens par fonctionnalite », « Part de chaque fonctionnalite », « Appels par fonctionnalite » ;
  - « Appels interrompus ou en erreur » ;
  - « Tokens d'entree par appel (mediane et p95) », « Tokens de sortie par appel (mediane et p95) » ;
  - « Tokens par seconde, par fonctionnalite », « Appels par seconde, par fonctionnalite et issue ».
- **4 panneaux fabriquent un zéro** : leur requête se termine par `or vector(0)` et leur `noValue` vaut `"0"`. Si la
  métrique n'est pas exportée du tout (instrumentation cassée, mauvais Prometheus, fonctionnalité jamais appelée), ils
  affichent **0**, exactement comme un état sain :
  - « Tokens consommes », « Appels IA », « Appels sans usage declare », « Tokens non attribues ».
- **Même motif ailleurs** : le panneau « Tokens de chat envoyes a OpenAI » de `mssante-mail-processing.json`
  (task-325), `or vector(0)` et `noValue` `"0"`.
- **Pourquoi le rouge est passé inaperçu 16 jours** : les tests du harnais (`tests/loadtest-k6/`, Python et JS) ne
  tournent ni dans la CI d'api-mail (`.github/workflows/dotnet.yml` ne lance que `dotnet test`), ni dans la validation
  d'une task qui ne touche pas le harnais. task-385 a modifié un tableau de bord sans que la règle qui le garde soit
  jouée.
- Convention du dépôt : `"noValue": "pas de donnee"` (87 panneaux).
- Le test actuel ne vérifie que la **présence** de `noValue`. Un `noValue` à `"0"`, ou un `or vector(0)`, le
  satisfait tout en le contredisant.

## Objective

Sur les tableaux de bord de l'AppHost, **un panneau sans donnée le dit**, et un zéro n'apparaît que lorsqu'il a été
mesuré. La règle est gardée par un test qui tourne en CI.

Règles :
- Tout panneau qui interroge une métrique porte un `noValue` explicite qui n'est **pas un chiffre** (convention :
  `pas de donnee`).
- **Un zéro se mesure, il ne se fabrique pas.** Un compteur sain peut valoir 0 (« Appels sans usage declare » vaut 0
  quand tout appel déclare son usage) : ce zéro n'est affiché que si la **métrique parente existe**. Exemple d'idiome :
  `sum(increase(X{usage="inconnu"}[$__range])) or (sum(increase(X[$__range])) * 0)`, qui rend 0 quand des appels
  existent sans aucun « inconnu », et rien (donc `pas de donnee`) quand la métrique est absente.
  `or vector(0)` est interdit.
- Le test garde les deux règles : `noValue` présent et non numérique, aucune requête en `or vector(0)`.
- **La règle tourne en CI** : les tests du harnais (`node --test lib/*.test.mjs` et
  `python -m unittest discover -p "test_*.py"` dans `tests/loadtest-k6/`) sont une étape de
  `.github/workflows/dotnet.yml`. Un tableau de bord modifié sans respecter la règle rend la PR rouge.

### Hors périmètre

- Le contenu des panneaux (métriques, labels, découpage par fonctionnalité) : inchangé.
- L'import en production : le JSON corrigé est celui à importer. L'import lui-même revient à l'humain (DevOps).
- Les autres règles des tableaux de bord (unités, task-224) : déjà gardées, inchangées.

## Definition of Done

- [ ] Build passes (0 errors) : `HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) : `HealthPlatform.Api.Mail.sln`, et `tests/loadtest-k6/selftest.sh` **entièrement vert**
- [ ] Les 8 panneaux sans `noValue` de `mssante-ai-consumption.json` portent `"noValue": "pas de donnee"`
- [ ] Les 5 panneaux en `or vector(0)` (4 dans `mssante-ai-consumption.json`, 1 dans
      `mssante-mail-processing.json`) ne fabriquent plus de zéro : zéro seulement si la métrique parente existe,
      `noValue` à `pas de donnee`
- [ ] `test_dashboards.py` refuse un `noValue` numérique et une expression contenant `or vector(0)`. Les deux
      nouvelles assertions sont **vues rouges** sur le JSON d'avant le correctif (preuve consignée dans le
      `## Develop log`, `python -B`, `__pycache__` effacé)
- [ ] Étape CI ajoutée à `.github/workflows/dotnet.yml` : `node --test lib/*.test.mjs` et
      `python -m unittest discover -p "test_*.py"` dans `tests/loadtest-k6/`. La CI de la PR est verte, et le
      `## Develop log` cite le run où l'étape apparaît
- [ ] Le test .NET existant `…TheConsumptionDashboard_OnlyQueriesSeriesThatTheApiExposes` reste vert avec les
      nouvelles expressions
- [ ] `docs/ia-fournisseurs.md`, § « Consommation par fonctionnalité » : une phrase sur la lecture de
      `pas de donnee` (métrique absente) face à `0` (mesuré)
- [ ] `conventions/csharp.md` : une entrée « Tableau de bord de l'AppHost — un panneau sans donnée le dit, un zéro se
      mesure ». C'est le fichier que `/develop` lit avant toute task `api-mail` : un fichier de conventions qu'aucun
      playbook n'impose ne serait pas lu (règle d'or, point 3)
- [ ] Aucune donnée de santé : les panneaux ne portent que des compteurs de tokens et d'appels

## Manual Test Plan

1. **Tests** : depuis `Api/Mail/tests/loadtest-k6`, `bash selftest.sh`. Tout est vert, `test_dashboards` compris.
2. **CI** : sur la PR, l'étape des tests du harnais apparaît dans le run GitHub Actions, verte.
3. **Tableau de bord sans donnée** : `cd Api/Mail && dotnet run --project src/AppHost`, sans aucun appel IA depuis le
   démarrage. Ouvrir Grafana, tableau de bord « Consommation IA par fonctionnalité » : chaque panneau affiche
   `pas de donnee`, aucun ne montre `0`.
4. **Tableau de bord avec données** : déclencher quelques appels IA (ouvrir un message analysé, poser une question à
   l'assistant). Les panneaux se remplissent. « Appels sans usage declare » affiche **0** (et non `pas de donnee`) si
   tous les appels déclarent leur usage.
5. Facultatif : importer le JSON dans le Grafana de recette, mêmes constats.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur. Outillage d'exploitation interne
- **Exigences DSR honorées** : non applicable. Aucun comportement visible du PS ne change
- **INS** : non applicable. Aucun trait d'identité patient
- **Authentification PS** : non applicable, inchangée
- **Habilitations** : non applicable, inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé. Aucun évènement de l'application n'est ajouté ni retiré
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non concerné. Les tableaux de bord ne lisent que des compteurs techniques (tokens, appels,
  fonctionnalité), sans donnée de santé
- **AIPD / impact RGPD** : inchangé, aucun traitement nouveau

## Branches

- `api-mail` (pushed) : fix/task-428-tableau-de-bord-ia-panneau-vide-jamais — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-428-tableau-de-bord-ia-panneau-vide-jamais

> Pré-flight du /start (2026-11-07) : `api-mail`, `client-blazor`, `client-mobile`, `dtos-mss`, `sdk` sur `develop`.

## Timings

*(généré par `tools/timing/report.sh --task task-428 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 15 s | — | — | — | — |
| /develop | ok | 10 min 52 s | 1 (8.2 s) | 1 (5 min 34 s) | — | api-mail 1B/1T |
| **Total cycle** | | **11 min 08 s** | **1 (8.2 s)** | **1 (5 min 34 s)** | **0 (0.0 s)** | |

## Develop log

**Correctif** (`api-mail`) :
- **`src/AppHost/grafana/dashboards/mssante-ai-consumption.json`** : 12 panneaux.
  - 8 panneaux reçoivent `"noValue": "pas de donnee"` : tokens, part et appels par fonctionnalité, appels interrompus,
    tokens d'entrée et de sortie par appel, débits de tokens et d'appels.
  - 4 panneaux perdent leur `or vector(0)` et leur `noValue: "0"` :
    - « Tokens consommes » et « Appels IA » n'ont que le filtre de variable `$feature` : `A` seul ;
    - « Appels sans usage declare » : `A or (sum(increase(mssante_ai_calls_total{feature=~"$feature"}[$__range])) * 0)` ;
    - « Tokens non attribues » : `A or (sum(increase(mssante_ai_tokens_total[$__range])) * 0)`.
- **`src/AppHost/grafana/dashboards/mssante-mail-processing.json`** : **17 panneaux en `or vector(0)`, et non 1 comme
  le relevait le task file**.
  - « Tokens de chat envoyes a OpenAI » (`noValue: "0"`, task-325) devient `A or (sum(increase(mssante_ai_tokens_total[$__range])) * 0)`,
    avec `noValue` `pas de donnee`.
  - 16 autres (e-mails, pipeline IA, synchronisation, recherche, actions en attente, CDA) avaient bien `noValue`
    `pas de donnee`, mais le `or vector(0)` le rendait inatteignable : ils affichaient 0 même sans métrique. Ils sont
    réécrits selon la même règle : `A or (P * 0)` quand `A` filtre un détail (`status`, `step`), `A` seul sinon.
  - La règle de la task (« `or vector(0)` est interdit ») les couvre, et le test étendu les aurait refusés.
- **Méthode** :
  - `mssante-ai-consumption.json` est réécrit structurellement (`json.dumps(indent=2)` reproduit le fichier à
    l'identique, vérifié avant) ;
  - `mssante-mail-processing.json`, dont le format n'est pas reproductible, est modifié par remplacement textuel des
    seules expressions et du `noValue` chiffré ;
  - les deux JSON sont relus valides.
- **Règle de réécriture** : `P` est `A` sans ses filtres de détail, avec les filtres de variable du tableau de bord
  (`$feature`). `A or (P * 0)` rend la mesure si elle existe, 0 si la métrique parente existe sans cette valeur, et rien
  (donc `pas de donnee`) si la métrique est absente.

**Tests** (`tests/loadtest-k6/test_dashboards.py`, classe `DashboardNoDataTests`) :
- `test_no_panel_says_zero_when_it_has_no_data` (nouveau) : aucun `noValue` numérique.
- `test_no_query_fabricates_a_zero` (nouveau) : aucune expression en `or vector(0)`.
- `test_every_queried_panel_says_when_it_has_no_data` (existant, rouge sur `develop` depuis task-385).
- **Preuve rouge sur le JSON d'avant le correctif** (`rm -rf __pycache__`, `python -B -m unittest test_dashboards`) :
  `FAILED (failures=3)`, les trois tests ci-dessus. Après le correctif : `Ran 7 tests … OK`.
- `bash selftest.sh` : **entièrement vert** sous Windows (Node et 419 tests Python), et **sous Linux** dans `node:22`,
  sur une copie en LF du dépôt (133 tests Node, 419 Python dont 8 ignorés), ce que la CI exécutera.
- Test .NET `AiConsumptionMetricsEndpointIntegrationTests.TheConsumptionDashboard_OnlyQueriesSeriesThatTheApiExposes` :
  vert avec les nouvelles expressions (les métriques parentes sont les mêmes séries).

**CI** (`.github/workflows/dotnet.yml`, job `build`) : étapes « Setup Node » (`actions/setup-node@v4`, Node 22) et
« Harness tests (tests/loadtest-k6) » (`bash selftest.sh`), avant .NET. Elles tournent sur toute PR vers `develop` ou
`master`, et sur tout push sur ces branches. Le run de la PR est cité dans `## PRs` par `/review`.

**Documentation** : `docs/ia-fournisseurs.md`, § « Le tableau de bord » : lecture de `pas de donnee` (métrique absente)
face à `0` (mesuré).

**Passe qualité (§Q)** : diff de configuration (JSON, YAML, test Python, documentation), relu directement : aucun
nettoyage à appliquer, aucune re-validation nécessaire.

**Prévention (règle d'or)** : entrée `tableau-de-bord-sans-donnee` dans `conventions/csharp.md`. C'est le fichier lu
par `/develop` avant toute task api-mail. L'entrée demande aussi de lancer `selftest.sh` avant de commiter un tableau
de bord. Garde en CI désormais.

## Sonar log

Analyse de la branche `fix/task-428-tableau-de-bord-ia-panneau-vide-jamais` (HEAD `f9e66826`), 2026-11-07 11:29 UTC :
- build Release, tests avec couverture OpenCover sur les 5 projets, **0 échec** ;
- traitement serveur `SUCCESS`, 0 itération (la task ne change aucun code C#).

### KPIs qualité (baseline → final)

| Métrique | Baseline (task-430) | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | = |
| Issues new code | 0 | 0 | = |
| New coverage | 96,0 % | 96,0 % | = |
| Bugs / Vulnérabilités / Code smells | 0 / 0 / 0 | 0 / 0 / 0 | = |
| Security hotspots | 0 | 0 | = |
| Coverage projet | 97,9 % | 97,9 % | = |
| Duplication | 0,4 % | 0,4 % | = |
| Ratings fiabilité / sécurité / maintenabilité | A / A / A | A / A / A | = |

## Lint log

Skipped — `client-angular` non touché par la task (`**Repos**: api-mail`).

## Lint mobile log

Skipped — `client-mobile` non touché par la task.
