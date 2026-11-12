# task-453 — `/e2e` bloqué : parité Angular (tests de task-445 perdus), sans lien avec la task

**Étape** : `/e2e` (porte `gate`, code 1). **Nature du blocage : parité**, pas une régression ni l'outillage.

## Ce qui est vert

- Voie **mobile** : 61 verts, 0 rouge.
- Voie **Angular** : 72 verts, 0 rouge, 2 flaky (E2E-SEARCH-001, E2E-LIVE-001), quarantaine E2E-COMPOSE-002 verte.
- Le scénario de la task, **E2E-BIO-004 v1**, est vert sur les deux clients (et avait été vu rouge sur le code non
  corrigé, voir le `## Develop log`).

## Ce qui bloque

La porte relève 6 écarts `MissingRequired [angular]` : **E2E-SEARCH-004, 005, 006, 007, 008, 009** sont requis pour
weda2 dans `Api/Mail/e2e/scenarios.yml` (ajoutés par **task-445**, déjà sur `develop`), mais aucun test de la suite
Angular ne les porte.

Origine établie :

- task-445 a écrit ces tests en mode code-only, **non commités**, sur `feature/nova-mss-weda-integration`
  (`tasks/archived/archived-task-445_…md`, `## Develop log` : « client-angular : aucun commit, à commiter par
  l'humain (TFS) »).
- Ils ne sont plus dans l'arbre de travail actuel, ni dans aucun commit du clone Angular :
  `git -C Client/Angular log --all -S E2E-SEARCH-004 -- front/e2e` ne rend rien.
- C'est la 2ᵉ occurrence du piège consigné `test-angular-non-commite` (`conventions/e2e.md`, après task-341).

task-453 ne touche ni la recherche ni ces tests : elle ne peut pas lever cet écart elle-même sans réécrire les tests
d'une autre task, ce qui sort de son périmètre (règle 6).

## Décision demandée à l'humain

Une des sorties légitimes de la porte :

1. **Restaurer les tests de task-445** dans `Client/Angular/front/e2e/mss-e2e/specs/functional.e2e.ts` (s'ils
   existent ailleurs : poste, stash TFS, autre clone), les commiter sur TFS, puis relancer `/e2e task-453`. La voie
   mobile sera réutilisée (cache vert), seule la voie Angular rejouera.
2. **Déclarer une divergence temporaire `angular`** sur E2E-SEARCH-004 à 009 dans `scenarios.yml` (raison + task de
   résorption, par exemple une task qui réécrit ces tests), puis relancer `/e2e task-453`.
3. **Bypass de `/e2e` pour task-453** (champ `**E2E**: bypass — décision humaine du …` dans le task file), si vous
   jugez la preuve suffisante : E2E-BIO-004 a été vu rouge puis vert sur les deux clients, et les deux voies sont
   vertes hors de cet écart.

## État des dépôts

- `api-mail` : `feat/task-453-un-acquittement-ne-disparait-jamais`, poussé (`ffc49e23`), arbre propre.
- `dtos-mss` : `feat/task-453-…`, poussé (`5ad659d`), NuGet 591.0.0 publié.
- `client-mobile` : `feat/task-453-…`, poussé (`8320106`), arbre propre.
- `client-angular` : code-only, 4 fichiers de la task **non commités** sur `feature/nova-mss-weda-integration`
  (modèle d'audit + spec, suite e2e : E2E-BIO-004 et helpers). **À commiter sur TFS avec, idéalement, les tests de
  task-445 restaurés.**
- Task laissée en `wip-*`. Aucune PR ouverte.

## Signalé au passage (non bloquant)

- **E2E-LIVE-001 [angular]** : 3ᵉ occurrence de flaky → task de stabilisation à ouvrir.
