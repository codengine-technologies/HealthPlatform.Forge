# questions/merge-task-218.md — `/merge task-218 --i-tested` interrompu sur la gate 5

**Date** : 2026-08-02
**Commande** : `/merge 218 --i-tested`
**Verdict** : **aucune PR mergée** (règle d'atomicité — soit toutes, soit aucune).

## État des gates

| Gate | SDK #2 | api-mail #146 | client-blazor #68 |
|---|---|---|---|
| 1 — `--i-tested` | ✅ fourni | ✅ | ✅ |
| 2 — pas `awaiting-us-completion` | ✅ `awaiting-human-merge` | ✅ | ✅ |
| 3 — pas de `CHANGES_REQUESTED` | ✅ aucune review | ✅ | ✅ |
| 4 — CI verte | ✅ `build` pass 38 s | ⚠️ aucun check configuré sur branche de feature | ✅ `build` pass 1 m 47 s |
| **5 — pas en retard sur `develop`** | ✅ `CLEAN` | ❌ **`CONFLICTING` / `DIRTY`** | ✅ `CLEAN` |
| 6 — arbre de travail propre | ✅ | ✅ | ✅ |

## Le blocage

Un seul commit de `develop` manque à la branche : **`f7c970b`** — *fix(mail) : un
UID ne peut plus résoudre vers le message d'une autre génération (task-179) (#144)*.

Un seul fichier est en conflit : **`Directory.Packages.props`**. Tout le reste
auto-fusionne, **y compris** les fichiers du chemin mail que task-179 touche
(`ImapService`, `ImapFolderService`, `MailRepository`, `FolderRepository`,
`ImapServicesFixture`, `UseCaseFixture`).

```
develop (task-179)  : HealthPlatform.Dtos.Mss   343.0.0 -> 377.0.0
task-218 (ma branche): HealthPlatform.Host.Sdk   10.0.0 -> 12.0.0
```

Ce sont **deux lignes adjacentes**, sur **deux paquets différents**. Il n'y a
donc **aucun conflit sémantique** : la résolution est de garder les deux
(`Dtos.Mss 377.0.0` **et** `Host.Sdk 12.0.0`). Git échoue seulement parce que les
modifications se touchent.

## Pourquoi ce n'est pas une formalité

La forme du conflit est triviale, sa **conséquence** ne l'est pas :

- l'attestation `--i-tested` a été donnée sur **`Dtos.Mss 343` + `Host.Sdk 12`** ;
- l'état mergeable est **`Dtos.Mss 377` + `Host.Sdk 12`** ;
- **cette combinaison n'a jamais été compilée**, et `Dtos.Mss` saute **34 versions
  majeures** (343 → 377). C'est le paquet de **contrats** partagé — un changement
  de contrat y est possible par construction.

Merger sans revalider reviendrait à poser sur `develop` une combinaison de paquets
que personne n'a construite ni testée.

## Conduite proposée

1. `git merge origin/develop` dans `Api/Mail` (règle 4 — **merge**, jamais rebase).
2. Résoudre `Directory.Packages.props` en gardant **les deux** bumps.
3. `dotnet build` + `dotnet test HealthPlatform.Api.Mail.sln` — la revalidation
   porte sur la combinaison réelle, pas sur celle testée.
4. Pousser, attendre la CI, puis relancer `/merge 218 --i-tested`.

⚠️ **Si l'étape 3 échoue** (contrat `Dtos.Mss` changé entre 343 et 377), ce n'est
plus un problème de merge : il faudra une correction, donc une nouvelle
validation humaine. Ne pas la court-circuiter au motif que le merge « était
trivial ».

## Note d'outillage

`gh pr checks 146` répond *« no checks reported on the branch »* : **api-mail n'a
pas de CI sur les branches de feature**. La gate 4 n'y mesure donc rien, et la
seule garde reste la vérification locale. À savoir avant de s'appuyer sur la
gate 4 pour ce repo.
