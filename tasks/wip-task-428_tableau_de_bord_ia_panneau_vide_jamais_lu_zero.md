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
