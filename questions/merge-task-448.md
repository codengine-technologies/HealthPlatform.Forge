> ✅ **Résolu le 2026-11-12** : resynchronisation faite par la forge à la demande de l'humain (DTOs 597.0.0), PRs #62 et #363 mergées, task archivée.

# merge-task-448 — `/merge` interrompu : la PR api-mail #363 est en conflit avec `develop`

**Date** : 2026-11-12. **Commande** : `/merge task-448 --i-tested`. **Rien n'a été mergé** : `/merge` est
atomique, et un garde-fou a échoué avant toute action.

## Garde-fous

| PR | État | Garde-fou |
|---|---|---|
| `dtos-mss` #62 | `MERGEABLE`, CI verte, label `awaiting-human-merge` | ✅ |
| `api-mail` #363 | **`CONFLICTING`** (`mergeStateStatus=DIRTY`) | ❌ garde 5 : branche en retard sur `develop` |

Garde 6 également en défaut sur `api-mail` : le clone porte des changements non commités. Ce n'est pas
task-448 : c'est la correction du classement de la recherche (branche `fix/recherche-debut-de-mot-et-proximite`,
demandée par l'humain le 2026-11-12, en attente de son feu vert pour le commit).

## Cause

`develop` a reçu task-453 (#364, `ee2f7533`) après l'ouverture de #363. Les deux tasks ont publié chacune un
paquet `HealthPlatform.Dtos.Mss` :

| Branche | Paquet DTO | Contient |
|---|---|---|
| `api-mail` `develop` | 591.0.0 | DTOs de task-453 (#63), pas ceux de task-448 |
| `api-mail` `feat/task-448-…` | 593.0.0 | DTOs de task-448, pas ceux de task-453 |

Les fichiers en conflit sont `Directory.Packages.props` et les `packages.lock.json`. **Aucun des deux paquets
ne convient** : choisir l'un ou l'autre ferait perdre les contrats de l'autre task.

## Reprise proposée

1. Synchroniser `dtos-mss` `feat/task-448-…` avec `origin/develop` (qui porte #63) : déjà `MERGEABLE`, la CI
   publiera un paquet qui contient les deux séries de DTOs.
2. Sur `api-mail` `feat/task-448-…` : `git merge origin/develop` (règle 4), résoudre en prenant ce nouveau
   paquet, régénérer les lock files (`dotnet restore --force-evaluate`), build + tests.
3. Relancer `/merge task-448 --i-tested`.

C'est la synchronisation que fait `/review task-448`. Décision humaine : relancer `/review`, ou laisser la forge
faire ces trois étapes directement.
