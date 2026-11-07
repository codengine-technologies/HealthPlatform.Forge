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
| /sonar | ok | 10 min 13 s | 1 (24 s) | 5 (8 min 25 s) | 2 (46 s) | api-mail 1B/5T |
| /lint-angular | skipped | 0.6 s | — | — | — | angular non touché |
| /lint-mobile | skipped | 0.6 s | — | — | — | mobile non touché |
| /e2e | ok | 19 min 31 s | — | — | — | e2e ×5 (37 min 57 s) |
| **Total cycle** | | **40 min 54 s** | **2 (32 s)** | **6 (14 min 00 s)** | **2 (46 s)** | |

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

## E2E log

Voies jouées le 2026-11-07 : `api-mail` à `f9e66826` (branche de la task), `client-mobile` à `develop`, `client-angular`
sur la branche du poste (code-only).

| Voie | Déclenchée par | Jouée / réutilisée | Résultat |
|---|---|---|---|
| mobile (`npm run e2e:headless`) | `api-mail` touché | jouée | ✅ 58 verts, 0 flaky, 0 rouge, parité verte |
| angular (`npm run e2e:mss`) | `api-mail` touché | jouée | ✅ 71 verts, 0 flaky, 0 rouge, parité verte |

Porte `gate` : code 0. Démontage vérifié : aucun conteneur e2e résiduel, aucun port du jeu e2e ouvert.

Aucun écran modifié : aucun scénario ajouté ni versionné (tableaux de bord et CI seulement).

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-PATIENT-003 | 1 | headless | La fiche d'un patient ne montre pas les documents d'un autre patient du même mail | ✅ | ✅ |
| E2E-PATIENT-004 | 1 | headless | La vue « Mails du patient » reste ouverte et ses pages viennent du serveur | ✅ | — |
| E2E-CONTACT-001 | 2 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 3 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-COMPOSE-004 | 1 | headless | Écrire à l'adresse choisie d'un contact à plusieurs adresses, ou à son adresse par défaut | ✅ | ✅ |
| E2E-COMPOSE-005 | 1 | headless | Une remise incertaine n'est jamais présentée comme un échec à renvoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-MAIL-006 | 1 | headless | Glisser sur la Corbeille un message d'un fil supprime ce message, et lui seul | ✅ | — |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-DRAFT-003 | 1 | headless | Quitter une rédaction récente ne perd rien | ✅ | ✅ |
| E2E-DRAFT-004 | 1 | headless | Une rédaction sans texte dans le corps ne laisse ni brouillon ni question | ✅ | ✅ |
| E2E-BIO-001 | 2 | headless | Acquitter un compte rendu de biologie, à son nom | ✅ | ✅ |
| E2E-BIO-002 | 1 | headless | La puce « Bio à acquitter » montre tous les résultats en attente, sur toutes les pages | ✅ | ✅ |
| E2E-BIO-003 | 1 | headless | Lire un résultat HPRIM puis l'acquitter | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SETTINGS-004 | 1 | headless | Paramètres indisponibles : rien n'est écrasé | ✅ | — |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 2 | headless | Créer un contact à deux adresses, le modifier sans les perdre, puis le supprimer | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-CONTACT-004 | 1 | headless | Consulter un contact depuis le carnet et lui écrire | ✅ | ✅ |
| E2E-CONTACT-005 | 1 | headless | Une fiche modifiée ne se perd pas sans confirmation, une adresse mal formée est refusée | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 2 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-MAILBOX-002 | 1 | headless | api-mail indisponible à l'entrée — écran de panne puis réessai | ✅ | ✅ |
| E2E-MAILBOX-003 | 2 | headless | Rattacher ses boîtes depuis « Mes boîtes » en un geste — titulaire et membre | ✅ | ✅ |
| E2E-MAILBOX-006 | 1 | headless | Après le rattachement, l'identité d'expéditeur et la signature sont déjà là | ✅ | ✅ |
| E2E-MAILBOX-004 | 1 | headless | Ajouter une BAL déléguée par saisie — et refus de sa propre adresse | ✅ | ✅ |
| E2E-MAILBOX-005 | 1 | headless | Le délégataire refusé par l'opérateur perd l'accès, en ligne puis hors ligne ; le titulaire garde le sien | ✅ | ✅ |
| E2E-AUDIT-001 | 1 | headless | Le titulaire lit au journal le message supprimé par son délégataire, au nom du délégataire | ✅ | — |
| E2E-AUDIT-002 | 1 | headless | Le journal d'audit montre chaque action sur un mail | ✅ | — |
| E2E-SHARED-001 | 1 | headless | Une boîte partagée, une base — le patient rattaché par le titulaire est vu du délégataire, la signature reste à chacun | ✅ | ✅ |
| E2E-SHARED-002 | 1 | headless | Le délégataire écrit pour le compte du titulaire — le destinataire voit qui a écrit, sa réponse revient à la boîte | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |
| E2E-SESSION-004 | 1 | headless | Sur un appareil partagé, la personne suivante n'arrive jamais dans la boîte de la précédente | ✅ | ✅ |
| E2E-AI-002 | 1 | headless | Un délégataire interroge l'assistant dans la boîte qu'il a ouverte | ✅ | ✅ |
| E2E-MAILBOX-007 | 1 | headless | Après un changement de boîte, l'onglet Patients ne montre plus rien de la précédente | ✅ | ✅ |
| E2E-ERROR-001 | 1 | headless | Une erreur affiche un code et une référence à transmettre au support | ✅ | ✅ |

**Parité : verte** — aucun écart entre le catalogue et les suites.

### CI de la PR (ajout au Develop log, `/review`)

- **Premier run de la PR** (42370267789) : **rouge** sur l'étape « Harness tests ». Les seuls échecs sont les 8 tests
  de `test_observe_push` (3 échecs, 5 erreurs).
  - La runner `ubuntu-latest` fournit `pwsh`, alors que ces tests n'étaient gardés que par la présence de PowerShell.
  - `observe.ps1` lit les classes CIM de Windows (`Win32_PerfFormattedData_*`) et ne peut rien échantillonner sous
    Linux.
  - L'essai local dans `node:22`, sans PowerShell, avait ignoré ces tests : il ne reproduisait pas la runner.
- **Correctif** (`5fdd64ce`) : ces tests exigent Windows **et** PowerShell (`CAN_SAMPLE`). Hors Windows, ils sont
  ignorés avec une raison explicite. Sous Windows, ils tournent toujours (8 OK).
- **Second run de la PR** (**42370394378**) : **vert**. Étapes « Setup Node » et « Harness tests (tests/loadtest-k6) »
  en succès, build .NET en succès.
- **Prévention** : mémoire de session `ci-runner-ubuntu-pwsh-tests-windows` : un test d'outil Windows se garde par
  `sys.platform`, et un essai Linux local n'est fidèle qu'avec les outils de la runner.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/349 — label `awaiting-human-merge`
  (commits `f9e66826` correctif, `5fdd64ce` garde Windows de l'échantillonneur). CI de la PR verte : run 42370394378.

## Code Review Summary

**APPROVED** — `/review` du 2026-11-07. Build : 0 erreur, 0 avertissement. Tests : domain 210, infrastructure 705, api
1 361, application 4 028, intégration 1 133 (+16 ignorés), **0 échec**. `selftest.sh` vert sous Windows et en CI.
Sonar : Quality Gate OK, 0 issue. E2E : vert.

- **Règle 1b** : sans objet. Aucun comportement atteignable par un endpoint ne change. Le test .NET des séries du
  tableau de bord de consommation reste vert.
- **DoD** :
  - 8 `noValue` ajoutés ;
  - 17 `or vector(0)` réécrits, et non 5 : le task file n'en relevait qu'un dans `mssante-mail-processing.json` ;
  - assertions vues rouges, puis vertes ;
  - étape CI présente et verte (run 42370394378) ;
  - documentation et consigne écrites.
- **Suggestion (non bloquante)** : `selftest.sh` ne fait pas échouer la CI quand Node ou Python manque (`MISSING=1`).
  Les deux sont fournis aujourd'hui, mais une runner sans Python sauterait les tests en silence.
