# questions/merge-task-297.md — `develop` est rouge après le merge de la PR #229

**Statut** : merge effectué (irréversible), `develop` d'`api-mail` ne compile plus sur la CI.
**Ouverte le** : 2026-09-13, par `/merge task-297 --i-tested` (étape 7, vérification CI post-merge).

---

## Le fait

- Squash `a2690a7` sur `develop`.
- Run CI : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/34746668197 — `build` **failure**, 10 erreurs.
- Toutes les erreurs sont **`xUnit1051`** et **toutes dans le seul fichier ajouté par task-297** :
  `tests/mss.mail.application.tests/Services/Cache/SizeBoundedCacheServiceTests.cs`
  lignes 39, 50, 53, 67, 80, 93, 95, 112, 136, 137.

  > Calls to methods which accept CancellationToken should use
  > `TestContext.Current.CancellationToken` to allow test cancellation to be more responsive.

## Pourquoi la PR était verte

`cf685ac — Migration to Xunit.V3 + update package` est sur `develop` et fait remonter
l'analyseur `xUnit1051` en **erreur**. La branche `feat/task-297-*` était basée sur
`5855604` (postérieur à la migration), mais son dernier run de PR (build **pass**, 1 m 47 s)
n'a pas produit ces erreurs — l'écart entre le build de la PR et celui de `develop`
reste **à établir** (commit contrôlé par le check ? configuration d'analyseurs
différente entre les deux déclencheurs ?). À vérifier avant d'en tirer une règle
générale : si le check de PR ne voit pas ce que voit `develop`, la garde « CI verte
avant merge » ne protège plus.

## Correctif

Mécanique : passer `TestContext.Current.CancellationToken` aux 10 appels concernés.
Ne touche que du test, aucun code de production.

## À arbitrer

1. Correctif immédiat en PR dédiée `fix(test): ...` vers `develop` (règle 5, merge humain) ?
2. Ou remis dans le flux d'une prochaine task ? — `develop` reste rouge en attendant,
   et la PR #232 (task-298) héritera d'un `develop` rouge.

**Recommandation** : (1). La PR task-298 est ouverte et sa validation dépend d'un
`develop` sain.
