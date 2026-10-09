> **Mise à jour du 2026-10-09, 2e passage de `/e2e`** : l'outillage est réglé, puisque l'humain a
> arrêté ses serveurs. Les deux voies ont tourné, démontage complet. **Blocage restant : RÉGRESSION
> connue, pré-existante, hors périmètre de la task.**
>
> | Voie | Résultat |
> |---|---|
> | mobile | ✅ 31 verts, parité verte |
> | angular | ❌ 30 verts, **1 rouge** : E2E-COMPOSE-002, « rédaction — corriger l'orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » ; parité verte |
>
> - **1er essai** : `Error: le transfert porte la citation d'origine`. `compose-body-editor` est vide
>   au lieu de contenir le message d'origine (`live-ai.e2e.ts:231`). C'est la signature du défaut
>   établi que corrige **task-350** : Transférer cliqué avant le chargement du contenu.
> - **2e essai** : `Error: le dossier INBOX est ouvert` (`support/weda.ts:78`), le titre de liste
>   n'apparaît pas. C'est la signature de l'incident de banc déjà vu sur task-353.
> - Traces : `Client/Angular/front/e2e/mss-e2e/out/test-results/live-ai.e2e.ts-rédaction-—-40a9e--arrive-la-citation-intacte-weda2-headless/`
>   (`trace.zip`, `error-context.md`), et le dossier `…-retry1/`.
> - **5e occurrence** de ce test au registre des flaky (`conventions/e2e.md`). Les quatre
>   précédentes étaient vertes au second essai. **C'est la première fois que les deux essais
>   échouent.**
>
> **Les deux sorties légitimes sont décidées par l'humain** (la forge ne pose jamais de quarantaine) :
> 1. **Quarantaine** du test Angular d'E2E-COMPOSE-002, dans
>    `Client/Angular/front/e2e/mss-e2e/specs/live-ai.e2e.ts` : tag `@quarantaine` et annotation
>    `{ type: 'quarantaine', description: 'task-350' }`. Le test continue de tourner et d'être
>    listé, mais ne bloque plus. Puis relancer `/e2e task-356`, qui enchaînera sur `/review`.
> 2. **Corriger d'abord task-350** (priorité 1, intégrité du message transféré), puis relancer
>    `/e2e task-356`.
>
> **Recommandation de la forge : 1, la quarantaine citant task-350.** Le défaut n'a aucun lien avec
> task-356, et task-350 est déjà ouverte pour le corriger. La quarantaine reste visible à chaque
> run et devient une alerte au-delà de 14 jours.

> **Mise à jour précédente (2026-10-09)** :
> - **Blocages 2 et 3 levés.** Le test d'intégration
>   `WedaIntegrationMissingFromEnvironment_TakesItsFailClosedDefault` est ajouté (commit api-mail
>   `7f2b260e`). Il a été vu rouge par mutation, et la preuve est consignée dans le
>   `## Develop log`.
> - **Blocage 1 toujours ouvert, motif OUTILLAGE.** `/e2e task-356` n'a pas pu lancer ses voies :
>   - le port **4200** est occupé par le serveur weda2 de l'humain ;
>   - le port **5052**, celui du backend e2e, est occupé par `dcp`, l'AppHost api-mail en cours.
>
>   Les voies n'ont pas été lancées, pour ne pas perturber cet environnement. La non-régression
>   n'est pas prouvée. **Action de l'humain** : arrêter le serveur weda2 et l'AppHost api-mail, puis
>   relancer `/e2e task-356`. Il enchaînera de lui-même sur `/review task-356`.

# questions/task-356.md — `/review` bloqué : verrous e2e et test d'intégration non satisfaits

**Étape** : `/review task-356` (2026-10-09), verrous 4a (règle 1b) et 4b (double verrou e2e).
**Décision attendue de** : aucune décision métier. Il y a trois actions de mise en conformité,
listées ci-dessous, puis il faut relancer `/review task-356`.
**Contexte** : la tâche a été implémentée **hors `/develop`**, à la demande de l'humain. Elle n'est
donc jamais passée par `/develop`, `/sonar` ni `/e2e`, qui produisent les preuves que `/review`
exige.

## Les blocages

### 1. `/e2e` non joué (verrou 4b, task-347) — bloquant

La tâche touche **api-mail** et **client-angular**, donc une voie e2e. Le task file doit porter un
`## E2E log` dont la ligne de verdict est verte. Il n'en a pas.

**Action** : `/e2e task-356`.

### 2. Un comportement exposé par une route sans test d'intégration (verrou 4a, règle 1b) — bloquant

| Comportement ajouté | Route | Test qui le prouve | Preuve rouge |
|---|---|---|---|
| `weda_integration` figure dans la réponse | `GET /api/v1/FeatureFlag` | `FeatureFlagEndpointIntegrationTests.AllFlagsPresent_ReturnsEveryDeclaredFlag`, qui parcourt `FeatureFlags.All` | aucune |
| **`weda_integration` absent de l'environnement Flagsmith → `false`** (repli de démarrage à froid déclaré fermé) | `GET /api/v1/FeatureFlag` | **aucun**. Le seul test de ce cas porte sur `ai_auto_tagging` | aucune |

Le second comportement est celui qui protège la production : tant que le flag n'a pas été créé
dans Flagsmith, aucune intégration Weda ne doit s'activer. Le test de convention
`WedaIntegration_IsDeclaredFailClosed` (tests unitaires) ne suffit pas, d'après la règle 1b.

**Action** :
- ajouter dans `FeatureFlagEndpointIntegrationTests` un cas
  `WedaIntegrationMissingFromEnvironment_TakesItsFailClosedDefault`. Il appelle
  `StartAsync(FeatureFlags.WedaIntegration)` et vérifie `flags["weda_integration"] == false` dans la
  réponse réelle ;
- **le voir rouge par mutation** : passer `[WedaIntegration] = true` dans `ColdStartDefaults`,
  constater l'échec, puis restaurer.

### 3. Pas de `## Develop log` — bloquant (conséquence du point 2)

La preuve rouge et la correspondance « comportement → test → preuve » doivent être consignées dans
un `## Develop log` du task file. Il n'existe pas : la tâche a un `## Avancement` à la place.

**Action** : créer le `## Develop log` avec la preuve par mutation du point 2.

## Ce qui a été revu et n'est pas bloquant

**Revue du code d'api-mail** (`git diff origin/develop...HEAD`, 3 fichiers) :
- `FeatureFlags.cs` — ✅ même motif que les flags existants : constante documentée, ajout à `All`,
  repli déclaré fermé et commenté ;
- `FlagsmithSeeder.cs` — ✅ semé ON en développement seulement, et la création DÉSACTIVÉE en
  recette et en production est documentée ;
- `FeatureFlagsConventionTests.cs` — ✅ l'ancrage littéral des flags fermés est étendu, et le nom du
  contrat est figé.

Le seul ❌ de la revue est la couverture (point 2, critère 5.6).

**client-angular** (dépôt code-only) n'a pas été revu dans ce passage : la revue s'arrête au premier
verrou. Pour mémoire, à la fin de l'implémentation : build `nx build weda2` OK, 2 654 tests weda2
verts, couverture de `lib/embedded` à 98,6 %, ESLint sans erreur. Le build et les tests ne sont pas
relancés ici. `/review` les relancera au prochain passage.

## Pour reprendre

1. Actions 2 et 3, sur la branche `feat/task-356-weda-integration-pont` d'api-mail.
2. `/e2e task-356` (action 1).
3. `/review task-356` : il revalidera build, tests, DoD, revue complète des deux dépôts, puis
   poussera la branche api-mail et ouvrira la PR.
