# questions/merge-task-275.md — `/merge` interrompu : CI rouge pour cause d'infrastructure

**Date** : 2026-08-30
**Commande** : `/merge 275 --i-tested`
**Statut** : **arrêté avant tout merge** — aucune PR mergée, aucune branche supprimée.

## Portes de sécurité

| Porte | Résultat |
|---|---|
| `--i-tested` présent | ✅ |
| Label `awaiting-us-completion` absent | ✅ (label posé : `awaiting-human-merge`) |
| Pas de review `CHANGES_REQUESTED` | ✅ (aucune review soumise) |
| Branche à jour avec `develop` | ✅ (`mergeable: MERGEABLE`) |
| Aucune modification non commitée | ✅ |
| **CI verte** | ❌ **`build-android` en échec** |

Une seule porte échoue.

## Pourquoi c'est un faux positif

L'échec **n'est pas un échec de build**. Le build Gradle va au bout (les tâches
`:capacitor-*` s'exécutent) ; le job meurt à l'étape d'**upload d'artefact** :

```
##[error]Failed to CreateArtifact: Artifact storage quota has been hit.
Unable to upload any new artifacts. Usage is recalculated every 6-12 hours.
```

C'est un quota GitHub Actions au niveau du compte/organisation, sans lien avec
le code.

**Le même échec, au même endroit, est présent sur `develop`** :

| Branche | Run | Date | Conclusion |
|---|---|---|---|
| `feat/task-275-mobile-psc-horizon` | 33325803765 | 2026-08-30 | failure — quota artefact |
| `develop` | 33215006645 | 2026-08-28 | failure — quota artefact |
| `develop` | 32559663506 | 2026-08-22 | failure |
| `develop` | 31719921405 | 2026-08-13 | failure |
| `develop` | 30151038991 | 2026-07-25 | failure |
| `develop` | 29602442241 | 2026-07-17 | ✅ **dernier succès** |

`Android Build` est donc rouge sur `develop` **depuis cinq semaines**.

## Ce que ça implique

- Merger task-275 **ne peut pas dégrader** la CI de `develop` : l'échec y est
  déjà, à l'identique, et pour une cause extérieure au dépôt.
- La règle 5 (« CI verte sur `develop` dans les 2 min après merge ») restera
  **non satisfaite après le merge**, quelle que soit la PR — c'est structurel
  tant que le quota n'est pas rétabli.
- Le diff de task-275 est **100 % test**, zéro ligne de code de production.
  Build local ✅, tests locaux ✅ **780/780**.

## Décision requise

`/merge` s'interdit de passer outre une porte rouge de lui-même. Le drapeau
`--i-tested` atteste du **test manuel**, pas d'une dérogation CI : ce sont deux
choses différentes, et la seconde appartient à l'humain.

Trois options :

1. **Autoriser explicitement le merge** malgré la CI rouge, sur constat que la
   cause est infrastructurelle et pré-existante. `/merge` reprend au point 3.
2. **Régler le quota d'abord** (purge des artefacts, ou attente de la
   recalculation 6-12 h), relancer la CI, puis relancer `/merge`.
3. **Rendre la porte robuste** : le workflow `Android Build` pourrait ne plus
   faire échouer le job sur un défaut d'upload d'artefact (`if-no-files-found`
   / `continue-on-error` sur la seule étape d'upload). C'est le correctif de
   fond — il rendrait la porte CI à nouveau signifiante au lieu d'être rouge
   en permanence, ce qui est le vrai risque ici : **une porte toujours rouge
   finit par être ignorée**.
