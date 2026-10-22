# questions/task-376.md — /review (4ᵉ passage) : revue APPROVED, synchronisation avec develop bloquée

**Étape** : `/review`, après la reprise B5.
**Revue de code : APPROVED** (B1–B5 corrigés, confirmés par la relecture ; voir `## Code Review Summary — 4ᵉ passage`).
**Blocage** : step 8 (« sync each branch with develop ») — conflit d'identifiant de scénario e2e avec task-379, mergée entre-temps. Aucune PR ouverte.

## Le conflit
- **task-379** (mergée sur `develop` : api-mail #304 `f8c1bfe7`, mobile #98 `c64490d`) a ajouté au catalogue **E2E-COMPOSE-004** « Écrire à l'adresse choisie d'un contact à plusieurs adresses, ou à son adresse par défaut », et monté **E2E-CONTACT-002 en v2**.
- **task-376** a créé, sur sa branche, **E2E-COMPOSE-004** « Une remise incertaine n'est jamais présentée comme un échec à renvoyer ». Même identifiant : le merge de `origin/develop` dans la branche api-mail entre en conflit sur `e2e/scenarios.yml`, et la parité deviendrait fausse.

## Résolution proposée (mécanique, sans changement de comportement)
1. **api-mail** : `git merge origin/develop` ; dans `e2e/scenarios.yml`, garder le E2E-COMPOSE-004 de task-379 et **renuméroter celui de task-376 en E2E-COMPOSE-005** ; garder E2E-CONTACT-002 v2.
2. **client-mobile** : `git merge origin/develop` ; renuméroter le test « remise incertaine » en `@E2E-COMPOSE-005`.
3. **client-angular** (code-only) : renuméroter le test « remise incertaine » de `functional.e2e.ts` en `E2E-COMPOSE-005`.
4. Rejouer `/e2e` (deux voies) puis finir `/review` (PRs).

## Point qui demande ta décision
- **Ton arbre weda2 ne porte pas le code Angular de task-379** : `functional.e2e.ts` y a encore E2E-CONTACT-002 en **v1** et n'a pas le E2E-COMPOSE-004 de task-379. Une fois le catalogue de `develop` fusionné, la voie Angular sera **rouge en parité** pour des raisons étrangères à task-376 (même famille que « angular-code-only perdu », mémoire `feedback_angular_codeonly_e2e_lost_parity`).
- Sorties possibles :
  - (a) tu ramènes d'abord dans ton arbre weda2 le code Angular de task-379 (commit TFS ou stash), puis je fais 1→4 ;
  - (b) je fais 1→4, et la parité Angular rouge est consignée comme héritée de task-379 (la porte bloquera : il faudrait alors ta décision explicite pour ouvrir les PRs malgré elle, ou une divergence temporaire au catalogue pour CONTACT-002 v2 / COMPOSE-004 côté angular, avec la task qui les résorbe).

## Rappel des autres points ouverts
- Jeton Sonar à faire tourner (fuite dans `metrics/timings.jsonl`, historique git).
- E2E-SEARCH-001 : 4 occurrences flaky → task de stabilisation à ouvrir.
- Suite de revue (non bloquant, task de suivi suggérée) : « Nouveau message » pendant un envoi en vol réinitialise la rédaction (préexistant) ; ligne `proposedDraftId = null` au retour de l'orphelin devenue redondante ; recréation `404 → POST` revenant après l'envoi (doublon rare).
