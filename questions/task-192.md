# questions/task-192.md — `/e2e` ROUGE : régression (E2E-DETAIL-002), vraisemblablement hors task

**Étape** : `/e2e` (voie mobile) — chaîne arrêtée avant `/review` (règle 13, fail-fast).
**Nature du blocage** : **régression** (pas parité, pas outillage — parité verte, démontage complet).

## Ce qui est rouge

| Client | Test | Scénario | Résultat |
|---|---|---|---|
| mobile | « détail — bascule texte brut / HTML » (`Client/Mobile/e2e/specs/functional.spec.ts:674`) | `E2E-DETAIL-002` v1 | ❌ rouge aux deux essais (`retries: 1`) |

Extrait d'erreur Playwright (sans donnée de santé — identité synthétique, corpus seedé) :

```
Error: [headless — donnée seedée attendue] mail sans corps affichable
expect(received).toBeTruthy()   Received: false
    at softSkip (e2e/support/headless.ts:89)
    at e2e/specs/functional.spec.ts:699
```

Le détail du message s'ouvre (barre d'actions rendue, bouton de bascule visible), mais **ni
`mail-body-html` ni `mail-body-plain` n'apparaissent** : l'écran reste sur `mail-body-empty`
pour le premier message de l'inbox seedée, alors que le seed lui donne un corps texte + HTML.

Traces :
- `Client/Mobile/e2e/test-results/functional-détail-—-bascule-texte-brut-HTML-headless/{trace.zip,error-context.md,test-failed-1.png}`
- idem suffixe `-retry1`
- rapports copiés : `%TEMP%/forge-e2e/task-192/mobile-report.json`, `mobile-summary.json`, `e2e-log.md`

Les 22 autres parcours headless sont verts, **dont `E2E-SEARCH-001`** (le parcours de recherche,
seul concerné par la task).

## Pourquoi la forge pense que ce n'est pas task-192 — sans pouvoir le prouver

- Le diff `api-mail` de task-192 ne touche **que** la recherche : `SemanticSearchRepository`,
  `SemanticSearchService`, `SearchController`, `SearchQueryHelper`, `SearchResultHelper`, modèles
  de résultats de recherche, plus le bump `HealthPlatform.Dtos.Mss` 492.0.0 (ajout pur de deux
  champs sur `SearchResponseDto`). Aucun fichier du chemin « lecture d'un message / corps /
  enrichissement ».
- Le parcours rouge n'appelle pas la recherche : il ouvre le premier message de l'inbox.
- Deux merges récents de `develop`, **antérieurs à la branche de task-192** et donc inclus dans le
  backend testé, portent précisément sur ce chemin :
  - `99bba666` fix(mail): l'enrichissement suit l'ordre de la liste du client, plus l'UID
  - `a9ebaa50` Merge chore/consolidate-maildb-migrations : schéma courrier consolidé en une seule SetupMigration
- La preuve formelle serait de rejouer la voie mobile avec l'`api-mail` de `origin/develop`. Cette
  étape interdit tout checkout (lecture seule), la forge ne l'a donc pas fait.

## Décision humaine attendue — une seule des trois

1. **Confirmer la provenance puis mettre en quarantaine** : rejouer `npm run e2e:headless` dans
   `Client/Mobile` avec `Api/Mail` sur `develop`. S'il est rouge aussi, poser la quarantaine sur le
   test (tag `@quarantaine` + annotation `quarantaine: task-NNN` citant une task de correction à
   ouvrir via `/po`), puis relancer `/e2e task-192` → la chaîne reprend vers `/review`.
2. **Corriger d'abord sur `develop`** (task dédiée), merger, synchroniser la branche de task-192
   (`git merge origin/develop`, règle 4), puis relancer `/e2e task-192`.
3. **Si le rouge disparaît sur `develop`** (donc imputable à task-192) : le signaler — la forge
   reprendra `/develop task-192` pour corriger, ce qui contredirait l'analyse ci-dessus.

## État laissé

- Task : `tasks/wip-task-192.md` (inchangée de statut), `## E2E log` écrit en rouge.
- Branches poussées, vertes (build + 5 970 tests) : `api-mail` `fix/task-192-search-exhaustive-dedup-case`
  (`74c20b50`), `dtos-mss` idem (`65440b3`, NuGet 492.0.0 publié).
- Aucune PR ouverte.
