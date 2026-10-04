# questions/task-333 — /e2e rouge, motif « parité » (sans rapport avec la task)

**Étape** : `/e2e`, après `/develop` et `/sonar` verts. La chaîne est arrêtée avant `/review`.

## Constat

- Voie mobile : **verte**, 29/29, parité verte.
- Voie Angular : **suite verte** (27/27), **parité rouge** :
  - `E2E-FOLDER-003` « Ouvrir un dossier supprimé depuis un autre logiciel » : requis pour angular, absent de la suite ;
  - `E2E-FOLDER-004` « Actualiser la liste des dossiers après un changement fait dans un autre logiciel » : requis pour angular, absent de la suite.
- Les deux scénarios viennent de **task-352** (mergée sur `develop` côté api-mail et mobile, `done-task-352.md`). Sa partie Angular était **code-only, non commitée**. Dans le checkout actuel (`Client/Angular`, branche `feature/nova-rewriting-mss`), aucun spec ne porte ces identifiants. Seuls les deux `environment.ts` restent modifiés. Le code Angular de task-352 a donc quitté l'arbre de travail (commit sur une autre branche, remisage, ou abandon).
- task-333 ne touche aucun client. Sa branche api-mail a dû fusionner `develop` pour embarquer le catalogue et l'outillage de task-352, ce qui rend ces deux scénarios requis.

## Décision humaine requise (une des deux)

1. **Remettre le travail Angular de task-352 dans le checkout** (spec `functional.e2e.ts` avec `E2E-FOLDER-003` / `004`, et le correctif `folderLoadError`), puis relancer `/e2e task-333`.
2. **Déclarer une divergence temporaire** pour angular sur ces deux scénarios dans `Api/Mail/e2e/scenarios.yml` (raison + task de résorption), puis relancer `/e2e task-333`.

La forge ne pose ni divergence ni quarantaine (règle de `/e2e`).

## Ce qui est prêt

- interop-cda : `fix/task-333-marqueur-analyse-garde-technique`, publié en 101.0.0.
- api-mail : `fix/task-333-marqueur-analyse-garde-technique`, poussée et à jour de `develop` (`8a546c07`). Build et tests verts, Sonar phase 1 verte.
