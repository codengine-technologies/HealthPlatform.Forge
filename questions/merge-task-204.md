# questions/merge-task-204.md — `/merge 204 --i-tested` avorté sur la garde 6

**Date** : 2026-07-31
**Commande** : `/merge 204 --i-tested`
**Verdict** : **aucune PR mergée** (règle d'atomicité — `agents/merge.md`, « Never partial-merge »).

## Le blocage

**Garde 6 — arbre de travail sale sur un repo cible.**

```
Api/Mail :  M tests/loadtest-k6/reports/INDEX.md   (+8 lignes, 0 suppression)
```

Ce n'est pas un résidu anodin : ce sont **les 8 lignes d'INDEX de l'escalier de
capacité du 2026-07-29**, c'est-à-dire l'artefact que la DOD de task-204 réclame
au titre de « Chaque palier a son rapport et sa ligne d'INDEX » — et que le
`## Escalier de capacité log` de la task coche déjà (`[x] Rapport + ligne
d'INDEX par palier`).

| Palier / tir | Délivré (plateau) | Abandons | Rapport |
|---|---|---|---|
| échauffement 200 praticiens | 473,6 req/s | 2,6 % | `report-mixed-mssante-60vu-201004.md` |
| budget 486 req/s | 482,7 | 0,7 % | `…-201816.md` |
| budget 630 req/s | 625,4 | 0,7 % | `…-202440.md` |
| budget 756 req/s | 745,5 | 1,2 % | `…-203059.md` |
| budget 882 req/s | 824,8 | 4,2 % | `…-203745.md` |
| budget 972 req/s | 857,9 | 7,4 % | `…-204427.md` |
| 882 req/s `tail=16` (discrimination) | 716,4 | 13,5 % | `…-205304.md` |
| 972 req/s `tail=16` (discrimination) | 683,3 | 23,9 % | `…-205951.md` |

**Si la PR merge en l'état, ces 8 lignes ne partent pas sur `develop`.** Les
rapports eux-mêmes (`reports/2026-07-29/*.md`, `.json`, `observe-*.csv`) sont
**gitignorés par conception** (`.gitignore:386` — `tests/loadtest-k6/reports/*`
avec la seule exception `!…/INDEX.md`) : ils vivent uniquement sur ce poste.
L'INDEX est donc la **seule** trace versionnée de la campagne qui a nommé le
facteur limitant de l'EPIC — et le point de départ documentaire de l'avant/après
que task-205 doit publier.

PR #130 touche déjà `INDEX.md` (+26/−13 : recalcul des débits au dénominateur
nommé), mais **pas** ces 8 lignes-là.

## Toutes les autres gardes sont vertes

| Garde | État |
|---|---|
| 1 — `--i-tested` | ✅ présent |
| 2 — label `awaiting-us-completion` | ✅ absent (label = `awaiting-human-merge`) |
| 3 — revue `CHANGES_REQUESTED` | ✅ aucune (`reviewDecision` vide) |
| 4 — CI rouge | ✅ verte (`build` pass 1 m 37 s ; `publish` skipped) |
| 5 — branche en retard / conflit | ✅ `MERGEABLE` / `mergeStateStatus: CLEAN` |
| 6 — arbre sale | ❌ **`api-mail`** (ci-dessus) |

`dtos-mss` : arbre **propre**, branche `feat/task-204-bench-resource-telemetry`
**sans commit**, aucune PR (conforme au `## PRs` de la task) — rien à merger,
seul le retour sur `develop` reste à faire.

## Trois issues, au choix de l'humain

### A — committer l'INDEX sur la branche, puis re-merger *(recommandé)*

L'escalier arrive sur `develop` avec le code qui l'a produit. Coût : un cycle CI
(~2 min) parce que la PR bouge après ton test — mais le diff est
**documentaire pur**, aucun risque de régression.

```bash
cd D:/TechWatch/HealthPlatform/Api/Mail
git add tests/loadtest-k6/reports/INDEX.md
git commit -m "docs(loadtest): lignes d'INDEX de l'escalier de capacité — task-204"
git push
# attendre la CI, puis :
/merge 204 --i-tested
```

### B — merger maintenant, publier l'INDEX ensuite sur `develop`

Débloque le merge tout de suite. L'INDEX arrivera par un commit direct sur
`develop` (ou dans la PR de task-205, qui doit de toute façon y écrire son
avant/après).

```bash
cd D:/TechWatch/HealthPlatform/Api/Mail
git stash push -m "index-escalier-204" tests/loadtest-k6/reports/INDEX.md
/merge 204 --i-tested
# après merge, sur develop : git stash pop && commit
```

⚠️ Le `stash` n'est **pas** une garantie : si la reprise est oubliée, la seule
trace versionnée de la campagne est perdue (les rapports sont gitignorés).

### C — abandonner les 8 lignes

À ne retenir que si tu juges l'escalier suffisamment consigné dans
`tasks/done-task-204.md` (§ « Escalier de capacité log », qui reprend les deux
courbes et l'expérience de discrimination). `git checkout --
tests/loadtest-k6/reports/INDEX.md` puis `/merge 204 --i-tested`.

## Note de contexte

`/start 205` a été refusé juste avant (pre-flight : `api-mail` et `dtos-mss` sur
`feat/task-204-…`). Ce merge est le déblocage attendu — une fois task-204
mergée et les deux repos revenus sur `develop`, `/start 205` passera.
