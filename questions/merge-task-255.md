# questions/merge-task-255.md — `/merge` bloqué : la CI d'api-mail est rouge sur une alerte de sécurité, et ce n'est pas cette PR

**Date** : 2026-08-13
**Étape** : `/merge task-255 --i-tested`
**État** : **aucune PR mergée**. `tasks/done-task-255.md` reste en `done-*`,
la branche `feat/task-255-serialisation-enrichissement` est intacte.

## Les portes de sécurité

| Porte | État |
|---|---|
| `--i-tested` fourni | ✅ |
| Label `awaiting-us-completion` absent | ✅ (label posé : `awaiting-human-merge`) |
| Aucune revue `CHANGES_REQUESTED` | ✅ (aucune revue) |
| Branche à jour avec `develop`, sans conflit | ✅ `MERGEABLE` |
| Aucun fichier non commité sur les repos cibles | ✅ |
| **CI verte** | ❌ **`build` = FAILURE** (`mergeStateStatus: UNSTABLE`) |

## Ce qui casse la CI

```
error NU1903: Warning As Error: Package 'SSH.NET' 2025.1.0 has a known
high severity vulnerability, https://github.com/advisories/GHSA-q939-rpr3-3284
```

L'échec tombe à l'étape **Restore**, avant toute compilation et tout test.

**Origine — dépendance transitive de l'outillage de test uniquement** :

```
mss.mail.integration.tests
├── Testcontainers (v4.12.0) ──────────► SSH.NET (v2025.1.0)
├── Testcontainers.PostgreSql (v4.12.0) ► Testcontainers ► SSH.NET
└── Testcontainers.Redis (v4.12.0) ─────► Testcontainers ► SSH.NET
```

`SSH.NET` n'est référencé **par aucun `.csproj`** directement, et n'entre dans
**aucun binaire livré** — seuls les tests d'intégration le tirent, via
`Testcontainers`.

## Ce n'est pas task-255, et c'est démontrable

1. **Le diff de la PR face à `origin/develop` est de 10 lignes de Markdown**
   (`tests/loadtest-k6/reports/INDEX.md`). Aucun `.csproj`, aucune référence de
   paquet, aucun code compilé.
2. **`develop` était verte le 2026-08-10** — les cinq derniers runs sur
   `develop` sont tous `success`, le plus récent datant du 10 août à 14:43.
3. L'avis de sécurité a donc été **publié entre le 10 et le 13 août**.
   `NuGetAudit` traite les alertes en erreurs : **toute PR du dépôt est rouge
   depuis**, et la prochaine exécution sur `develop` le sera aussi.

## Pourquoi je m'arrête plutôt que de forcer

Merger exigerait `gh pr merge --admin`, c'est-à-dire **passer outre un contrôle
requis en échec**. Le contenu de cette PR est inoffensif (un fichier Markdown),
mais trois raisons rendent la décision tienne :

- la règle 5 du CLAUDE.md demande une **CI verte sur `develop` dans les deux
  minutes qui suivent le merge** — c'est impossible ici, et le restera ;
- passer outre une alerte **de sévérité haute** installe un précédent : la
  prochaine fois, le contrôle ignoré pourrait porter sur autre chose ;
- surtout, **le vrai travail à faire n'est pas de merger task-255** : c'est de
  débloquer la CI du dépôt, qui bloque *toutes* les PR.

## Options

**Option A — recommandée. Débloquer la CI d'abord.** Une US courte qui épingle
`SSH.NET` à une version corrigée dans `mss.mail.integration.tests` (référence
directe pour surclasser la transitive), ou qui remonte `Testcontainers` si une
version corrigée existe. La CI redevient verte pour **toutes** les PR en attente,
et task-255 se merge ensuite normalement, sans dérogation. Elle traite en outre
une alerte de sévérité haute au lieu de la contourner.

**Option B — merger task-255 en dérogation** (`gh pr merge 185 --squash
--admin`), puis traiter la vulnérabilité séparément. Défendable vu le contenu
(Markdown seul), mais laisse `develop` rouge et la dérogation documentée nulle
part ailleurs qu'ici.

**Option C — attendre** qu'un correctif amont de `Testcontainers` sorte. Non
recommandé : la date est inconnue et toutes les PR restent bloquées.

## Rappel — un second rouge, indépendant, déjà signalé

`AiPromptHelperTests.GetPromptShouldContainDocumentIntroduction` échoue **en
local** de façon déterministe : le commit `411b289` « Fix prompt » (sur
`develop` depuis le 2026-08-10) a modifié le texte du prompt sans mettre à jour
son test. La CI ne l'atteint pas — elle meurt avant, au Restore. Ce sont **deux
problèmes distincts**, et l'option A ne règle que le premier.
