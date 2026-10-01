# questions/task-338.md — `/e2e` ROUGE sur la voie Angular : **parité + régression**, causées par le travail de task-349 présent dans le checkout Angular

**Étape** : `/e2e` — chaîne arrêtée avant `/review` (règle 13, fail-fast).
**Nature du blocage** : **parité** et **régression** (voie Angular), portées par **un même test** qui n'appartient pas à task-338. Voie mobile : **verte** (24/24, parité verte).

## Ce que dit la porte

```
E2E : ROUGE — 2 motif(s) de blocage.
- [angular] rouge : « rédaction — corriger l'orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002)
- [angular] parité UnknownIdentifier : … (live-ai.e2e.ts, projet weda2-headless) porte l'identifiant E2E-COMPOSE-002, inconnu du catalogue.
Flaky (non bloquant) : [angular] « assistant — résumé initial puis deux questions de suite » (E2E-AI-001)
```

Extrait d'erreur Playwright (aucune donnée de santé) : `TimeoutError: locator.click: Timeout 15000ms exceeded`, puis `page.waitForResponse: Test ended`.
Rapports : `%TEMP%/forge-e2e/task-338/{mobile,angular}-report.json`, log de la porte `…/e2e-log.md`, traces sous `Client/Angular/front/e2e/mss-e2e/out/`.

## Pourquoi ce n'est pas task-338

- Le test `E2E-COMPOSE-002` vit dans `Client/Angular/front/e2e/mss-e2e/specs/live-ai.e2e.ts`, ajouté sur la branche humaine **`feature/nova-rewriting-mss`** par le commit **`6321706c`** « Update sur l'écran de saisie d'un nouveau mail + orth IA » — c'est le travail de **task-349** (correction orthographique, en cours sur une autre machine).
- Son identifiant n'est **pas** au catalogue de la branche api-mail de task-338 (ni de `develop`) : d'où l'écart de parité.
- Le backend testé est celui de task-338, qui n'a pas la correction orthographique : d'où le rouge.
- task-338 ne touche que la recherche (`api-mail` + contrat `SearchResponseDto`). Sur les deux voies, **tous les autres parcours sont verts**, dont la recherche (`E2E-SEARCH-001`, `E2E-INBOX-001`).

## Décision humaine attendue — une seule

La voie Angular rejoue **le checkout courant**, choisi par l'humain (mode code-only : la forge ne fait aucun checkout sur `client-angular`).

1. **Rejouer sur une branche Angular sans le travail de task-349** (recommandé) : basculer `Client/Angular` sur `next` (ou toute branche sans `6321706c`), puis relancer `/e2e task-338`. Les autres parcours étant verts, la chaîne reprendra vers `/review`.
2. **Ou attendre que task-349 soit mergée** (son scénario `E2E-COMPOSE-002` entrera alors au catalogue de `develop`), synchroniser la branche de task-338 (`git merge origin/develop`, règle 4), puis relancer `/e2e task-338`.
3. **Ou déclarer une quarantaine / une divergence temporaire** sur `E2E-COMPOSE-002` — décision de l'humain seul, peu adaptée ici puisque le test est correct pour la task qui l'apporte.

## Incident d'outillage résolu en route (prévention posée)

Premier passage de la voie Angular : **code 2** — `@playwright/test` déclaré dans `package.json` mais absent de `node_modules` (clone en retard sur le lockfile). Restauré par `npm ci` (ne touche que `node_modules`, aucun fichier suivi). Prévention : **Step 0 bis** ajouté à `agents/e2e.md` (vérifier le paquet avant chaque voie, sinon `npm ci` mesuré) — non poussé, à relire (règle d'or, point 7).

## État laissé

- Task : `tasks/wip-task-338.md`, `## E2E log` écrit en rouge.
- Branches poussées, vertes : `api-mail` `fix/task-338-search-tells-the-truth` (`7fa67268`), `dtos-mss` idem (`2aa32a7`, NuGet 496.0.0 publié).
- Aucune PR ouverte.
