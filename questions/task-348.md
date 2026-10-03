# task-348 — `/e2e` ROUGE : voie Angular (régression ou fragilité + parité), étrangers au code de la task

**Date** : 2026-10-03
**Étape** : `/e2e` (bloquante, sans exemption). Chaîne arrêtée avant `/review`. La task reste en `wip-*`.
**Verdict de la porte** : ROUGE (code 1), 3 motifs bloquants, tous sur la voie **Angular**.
**Voie mobile** : verte (26 réussis, 0 flaky, 0 rouge, parité verte). Elle prouve le comportement de task-348 côté backend : le banc e2e résout son serveur depuis le domaine `e2e.test` déclaré par l'AppHost, et plus par les réglages.

## Les 3 motifs

| # | Nature | Test (Angular, `functional.e2e.ts`) | Constat |
|---|---|---|---|
| 1 | **Parité** — `UnknownIdentifier` | `patients — rattacher à la main un document sans INS à une fiche cherchée par son nom` (`E2E-PATIENT-002`) | Identifiant inconnu du catalogue d'api-mail (branche task-348). Il n'existe que sur `origin/fix/task-331-dossier-patient-par-fiche`, **non mergée**. |
| 2 | **Rouge** | même test (`E2E-PATIENT-002`), rouge aux deux essais | `TypeError: Cannot read properties of undefined (reading 'lastName')` à `functional.e2e.ts:114` (`patientToAttach.lastName`) : la donnée de seed que le test attend n'existe pas dans le seed de la branche task-348. |
| 3 | **Rouge** | `recherche — requête et recherche avancée` (`E2E-SEARCH-001`), rouge aux deux essais | `la requête porte les termes saisis` : `Expected substring "Réunion"`, `Received ""` (`functional.e2e.ts:465`). Le test capture la **première** requête dont l'URL contient `/api/v1/search/` ; le client appelle aussi `GET /search/suggestions` et `GET /search/history`, sans corps. Le test a très probablement capturé l'une d'elles au lieu du `POST /search/semantic` : c'est à confirmer dans la trace. Le même scénario est **vert** sur la voie mobile. |

Traces : `Client/Angular/front/e2e/mss-e2e/out/test-results/functional.e2e.ts-patients-f244d--fiche-cherchée-par-son-nom-weda2-headless*/` et `…/functional.e2e.ts-recherche-—-requête-et-recherche-avancée-weda2-headless*/` (`trace.zip`, `error-context.md`). Rapports copiés : `%TEMP%\forge-e2e\task-348\`.

## Pourquoi ce n'est pas task-348

- La voie Angular joue la branche **extraite par l'humain** dans `Client/Angular` (`feature/nova-rewriting-mss`, code-only). Elle contient manifestement le travail de **task-331** (test `E2E-PATIENT-002` et donnée de seed `patientToAttach`), absent du backend et du catalogue de task-348.
- task-348 ne modifie côté Angular que l'écran Paramètres (`mss-settings.component.*`), le modèle des réglages et `MssApiService.getMailServer()`. Ni la recherche, ni les patients, ni leurs tests.
- La règle `/e2e` est **sans exemption** (un rouge étranger bloque comme un rouge propre) : la forge s'arrête et ne pose ni quarantaine ni divergence.

## Décisions possibles (humain seul)

1. **Rejouer la voie Angular sur une branche sans le travail de task-331** (par exemple `next` à jour), puis relancer `/e2e task-348`. C'est la sortie la plus probable si le rouge de recherche vient aussi de cette branche.
2. **Quarantaine** de `E2E-SEARCH-001` côté Angular (tag `@quarantaine` + annotation citant une task de correction du test, qui doit attendre `POST /api/v1/search/semantic` et non toute URL `/search/`), si le rouge persiste sur une branche propre.
3. Pour `E2E-PATIENT-002` : il disparaît de lui-même une fois task-331 mergée (catalogue et seed à jour), ou si la branche Angular ne le porte pas pendant le run.

Une fois la décision prise : `/e2e task-348`, puis la chaîne reprend (`/review` → `/tech-writer`).
