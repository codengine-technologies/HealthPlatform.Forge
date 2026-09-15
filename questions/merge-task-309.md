> # ✅ RÉSOLU le 2026-09-15 — les deux bloqueurs sont corrigés, task-309 est mergée.
>
> - **Bloqueur 1** (casse `src`/`Src`) : corrigé par `6a2b559` sur `client-blazor` —
>   la page est localisée par `git ls-files`, garde ré-éprouvée.
> - **Bloqueur 2** (package SDK `tools`) : corrigé par `1cb0ba4` sur `client-mobile`,
>   porté sur la branche task-309 (arbitrage humain). `develop` mobile est **vert**
>   pour la première fois depuis le 2026-09-14.
>
> PRs mergées : blazor #76 (`5733722`), mobile #72 (`f10e1bc`).
> Bilan : `tasks/archived/archived-task-309.md`, section `## Merged`.
> Ce fichier est conservé pour la valeur de l'analyse, pas comme bloqueur ouvert.

# questions/merge-task-309.md — `/merge` refusé : CI rouge sur les deux PRs

**Date** : 2026-09-15
**Commande** : `/merge 309 --i-tested`
**Verdict** : **aucune PR mergée** — la garde 4 (« CI rouge ») échoue. Le lot est
atomique : rien n'est mergé tant qu'un bloqueur subsiste (agents/merge.md, §Safety).

Les gardes 1, 2, 3, 5 et 6 passent :

| Garde | client-blazor #76 | client-mobile #72 |
|---|---|---|
| 1 — `--i-tested` | ✅ fourni | ✅ fourni |
| 2 — label | ✅ `awaiting-human-merge` | ✅ `awaiting-human-merge` |
| 3 — revue | ✅ aucun `CHANGES_REQUESTED` | ✅ aucun `CHANGES_REQUESTED` |
| 4 — **CI** | ❌ **`build` FAIL** | ❌ **`build-android` FAIL** |
| 5 — mergeable | ✅ `MERGEABLE` (pas `BEHIND`/`CONFLICTING`) | ✅ `MERGEABLE` |
| 6 — arbre propre | ✅ rien de non commité | ✅ rien de non commité |

Les deux rouges n'ont **pas la même nature**, et un seul est imputable à la task.

---

## Bloqueur 1 — client-blazor : un test **de cette task** échoue en CI (réel)

[Run 34946663127](https://github.com/codengine-technologies/HealthPlatform.Client/actions/runs/34946663127/job/104307575471)
— 242 tests, **1 échec** :

```
Failed HealthPlatform.Module.Mss.Plugin.Tests.MailboxSwitcherMountGuardTests.Mail_Page_Mounts_The_Mailbox_Switcher
  page introuvable : /home/runner/work/.../src/Modules/Mss/Plugin/Pages/Mail.razor
```

Le test en échec est **celui que task-309 a ajouté** — la contre-épreuve du défaut
de l'US. Ce n'est ni un flaky, ni une dette préexistante : `develop` est **vert**
sur client-blazor (dernier run du 2026-09-14 21:04 → `success`). Merger #76 en
l'état **fait passer `develop` au rouge**.

### Cause — casse du chemin, invisible sous Windows

`MailboxSwitcherMountGuardTests.cs:28` construit le chemin en dur :

```csharp
var page = Path.Combine(
    RepoScan.RepoRoot(),
    "src", "Modules", "Mss", "Plugin", "Pages", "Mail.razor");   // ← "src" minuscule
```

Or le chemin réellement versionné est **`Src/Modules/Mss/Plugin/Pages/Mail.razor`**
(`S` majuscule — vérifié par `git ls-files`). Sous Windows, système de fichiers
insensible à la casse, le test passe ; sur le runner Linux de la CI, il échoue.
C'est pourquoi le vert local de `/develop` et de `/review` n'a rien vu.

C'est la **même classe de piège** que le répertoire `Tools/` du plan de contrôle :
ça marche à l'exécution locale, et c'est faux dès qu'un système sensible à la
casse lit le chemin.

### Aggravant — le test échoue sur sa première assertion, pas sur son objet

`Assert.True(File.Exists(page))` échoue **avant** le `Assert.Contains("<MailboxSwitcher", …)`.
Autrement dit, la garde n'a **jamais** vérifié ce qu'elle prétend garder. Elle est
verte localement pour une raison sans rapport avec le montage du sélecteur, et
rouge en CI pour une raison sans rapport non plus. Un correctif de casse seul la
rendrait verte — mais il faut **vérifier qu'elle est encore capable d'échouer**
(retirer la ligne `<MailboxSwitcher` de `Mail.razor`, constater le rouge, la
remettre), sinon on remplace une garde inopérante par une garde non éprouvée.

### Correctif proposé (non appliqué — `/merge` ne modifie pas de code)

1. `"src"` → `"Src"` dans `MailboxSwitcherMountGuardTests.cs:28`.
2. Mieux : passer par `RepoScan.TrackedFiles(...)` comme les deux autres gardes
   du même projet (`ClientSensitiveDataScanTests`, `SdkReferenceGuardTests`).
   Elles lisent `git ls-files`, donc la casse exacte du dépôt, et ne peuvent pas
   diverger. Ce nouveau test est **le seul du projet à coder un segment de chemin
   en dur** — c'est précisément ce que l'extraction de `RepoScan` (passe qualité
   de task-305) cherchait à éviter.
3. Ré-éprouver la garde (cf. ci-dessus), puis pousser sur
   `fix/task-309-selecteur-messageries-atteignable` et relancer `/merge`.

---

## Bloqueur 2 — client-mobile : panne d'outillage CI **préexistante** (non imputable)

[Run 34946735137](https://github.com/codengine-technologies/HealthPlatform.Mobile/actions/runs/34946735137/job/104307811176)
— le job `build-android` meurt **avant toute compilation**, dans l'action
`android-actions/setup-android@v3` :

```
Warning: Failed to find package 'tools'
Error: The process '/usr/local/lib/android/sdk/cmdline-tools/16.0/bin/sdkmanager' failed with exit code 1
```

Aucun code de la task n'est exercé : ni `npm ci`, ni le build, ni les tests. Le
package SDK `tools` est **obsolète** et n'est plus servi par le `sdkmanager` des
images runner récentes.

**Cette panne est déjà sur `develop`** : le run du 2026-09-14 21:04
([34896682052](https://github.com/codengine-technologies/HealthPlatform.Mobile/actions/runs/34896682052))
échoue avec **exactement le même message**, et c'est la première rupture après
une série verte remontant au 2026-08-30. Elle est donc **antérieure à task-309**
et sans lien avec elle.

Deux conséquences, à ne pas confondre :

- **Elle ne dit rien sur la qualité de la PR #72.** Le code mobile de task-309 a
  été validé localement (`/develop`, `/lint-mobile`, `/review` — build + tests
  verts, cf. `## Timings` du task file).
- **Elle bloque quand même la garde 4**, qui est binaire. Et surtout, elle prive
  la règle 5 du CLAUDE.md (« CI verte sur `develop` dans les 2 min après merge »)
  de tout signal sur ce repo : merger à l'aveugle ici, c'est perdre le filet pour
  toutes les tasks mobiles suivantes, pas seulement celle-ci.

### Ce qu'il faut décider — arbitrage humain

C'est une **panne d'infrastructure CI**, hors périmètre de task-309. Trois voies :

1. **Réparer la CI mobile d'abord** (recommandé) — retirer `tools` de la liste des
   packages demandés à `setup-android`, ou épingler l'action/les `packages:` sur
   des composants encore servis. C'est une task `devops`/`client-mobile` à part
   entière : elle débloque **toutes** les PRs mobiles, pas seulement #72, et
   restitue le filet de la règle 5. `develop` étant déjà rouge, elle est de toute
   façon à faire.
2. **Merger #72 en connaissance de cause**, en actant que la CI mobile est
   aveugle depuis le 2026-09-14. `/merge` ne le fera pas seul — il faudrait
   `gh pr merge 72 --squash` à la main, et la garde 4 resterait violée par
   décision explicite, pas par omission.
3. **Tout garder en attente** jusqu'à la réparation.

La voie 1 est la seule qui laisse `/merge task-309 --i-tested` repassable tel quel.

---

## Ce qui n'a PAS été fait (conséquence de l'abandon atomique)

- Aucune PR mergée, aucune branche supprimée, aucun `develop` synchronisé.
- **Branche vide `dtos-mss`** (`fix/task-309-selecteur-messageries-atteignable`,
  auto-incluse par `/start`, zéro commit) : **non nettoyée**. Elle l'est à l'étape
  5 bis, qui suit le merge. Elle rejoint donc pour l'instant les branches fantômes
  relevées le 2026-09-14.
- **Task non archivée** : reste `tasks/done-task-309.md`.
- **Branche de staging** : non touchée (l'étape 9 suit l'archivage).
- **client-angular** : hors périmètre `/merge` — la PR TFS et le clone local
  restent le domaine exclusif de l'humain, comme toujours.

## Pour reprendre

Une fois le bloqueur 1 corrigé et poussé (et le bloqueur 2 arbitré) :

```
/merge 309 --i-tested
```

Les gardes seront rejouées intégralement — l'attestation `--i-tested` porte sur la
US, que ces correctifs ne changent pas fonctionnellement.
