# merge-task-457 — PRs en conflit avec `develop` (gate 5)

**Étape** : /merge task-457 --i-tested (2026-11-18)
**Verdict** : arrêt avant tout merge (atomique) — aucune PR mergée.

## Constat

task-487 (« Conversation en chat ») a été mergée sur `develop` après l'ouverture des PRs de task-457 :
api-mail `fab760ec` (#375), client-mobile `6ad9830` (#130).

| PR | État | Gates |
|---|---|---|
| dtos-mss #70 | MERGEABLE, CLEAN | CI verte |
| api-mail #374 | **CONFLICTING** | CI verte sur la branche |
| client-mobile #129 | **CONFLICTING** | CI verte sur la branche |

Fichiers en conflit (`git merge-tree` contre `origin/develop`) :

- api-mail : `Directory.Packages.props` — les deux tasks ont monté `HealthPlatform.Dtos.Mss` (623.0.0 pour task-457).
  Une fois dtos-mss #70 mergée, il faut une version du paquet qui porte **les deux** contrats, publiée depuis
  `develop`, puis rebumper api-mail (et ses `packages.lock.json`).
  `e2e/scenarios.yml` et `UseCaseFixture.cs` sont fusionnés automatiquement, à relire.
- client-mobile : `e2e/specs/functional.spec.ts` (scénarios ajoutés en fin de fichier par les deux tasks),
  `mail-detail.component.ts` et `mail-detail.component.scss`.

## Ce qu'il faut

Synchroniser les deux branches avec `develop` (merge, jamais rebase — règle 4), résoudre, rebumper le paquet DTO,
rejouer build + suites complètes et les deux voies e2e, puis relancer `/merge task-457 --i-tested`.
C'est la synchronisation de `/review` (étape 8) : la forge peut la faire sur demande.

Merger dtos-mss #70 seule ne casse rien (elle est propre), mais `/merge` est tout ou rien par task : elle attend.
