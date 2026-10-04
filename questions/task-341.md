# questions/task-341 — `/e2e` bloqué : écart de PARITÉ côté Angular (sans lien avec la task)

**Étape** : `/e2e` (porte `gate`, code 1). **Nature : parité**, ni régression ni outillage.
**État** : task en `wip-task-341.md`. `/develop` et `/sonar` sont terminés et la branche api-mail
`feat/task-341-no-health-data-in-logs` est poussée (`6ed2d95b`). `/review` n'a **pas** été lancé.

## Ce que la porte a constaté

- Voie **mobile** : verte, 30 verts, parité verte.
- Voie **angular** : 29 verts, **0 rouge**, mais un écart de parité :
  `MissingRequired` [angular] **E2E-MAIL-005** (« Un message supprimé depuis un autre logiciel quitte
  la liste et ne s'ouvre jamais vide »), requis pour angular au catalogue, absent de la suite Angular.

## Pourquoi ce n'est pas task-341

- task-341 ne touche ni le catalogue (`git diff origin/develop...HEAD -- e2e/scenarios.yml` est vide),
  ni aucun client. Seule la voie Angular est jouée, parce qu'`api-mail` a changé.
- `E2E-MAIL-005` a été ajouté par **task-353** (api-mail #275, archivée), avec mobile **et** angular
  requis. Son test Angular a été écrit et prouvé rouge, puis vert, dans
  `Client/Angular/front/e2e/mss-e2e/specs/functional.e2e.ts`, mais en **mode code-only** : il n'a
  jamais été commité par la forge.
- Aujourd'hui, ce test n'existe dans **aucun** commit (`git log --all -S E2E-MAIL-005` vide), aucun des
  4 stash, ni l'arbre de travail de `Client/Angular`, sur `feature/nova-rewriting-mss` @ `30b27715`. Le
  reste des modifications Angular de task-353 (état, rafraîchissement, détail) a sans doute disparu
  avec lui : à vérifier.

## Décision attendue de l'humain (une des deux sorties légitimes)

1. **Restaurer le travail Angular de task-353** (test `E2E-MAIL-005` et correctifs) sur la branche
   Angular, depuis l'endroit où il a été commité ou conservé, puis relancer `/e2e task-341`. La chaîne
   reprend ensuite d'elle-même vers `/review`.
2. **Ou déclarer une divergence temporaire** au catalogue, sur `E2E-MAIL-005` pour `angular`, avec une
   raison et une task de résorption (`task-NNN`), puis relancer `/e2e task-341`.

La forge ne pose ni divergence ni quarantaine, et ne touche pas à git sur `client-angular`.

## Rappel

Tant que ce point n'est pas réglé, **toute** task qui touche `api-mail`, `client-angular` ou `dtos-mss`
bloquera au même endroit.
