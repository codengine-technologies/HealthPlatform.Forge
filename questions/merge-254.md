# questions/merge-254.md — `/merge 254 --i-tested` refusé

**Date** : 2026-08-10
**Commande** : `/merge 254 --i-tested`
**Verdict** : **refusé, aucune PR mergée, rien touché.**

## Pourquoi le refus

Deux garde-fous échouent, et le second est rédhibitoire.

### 1. La task n'est pas passée par `/review`

Elle est en **`tasks/wip-task-254.md`**, pas en `done-*`. Le fichier ne porte
**ni** `## PRs`, **ni** `## Code Review Summary` — les deux sections que `/merge`
lit pour savoir quoi merger. C'est le cas que le mode d'emploi de `/merge`
exclut explicitement : « If the task is still in `wip-*` or `review-*`. Run
`/review` first. »

### 2. Il n'existe aucune PR à merger

`gh pr list --state all --search "254"` ne rend **rien** : aucune PR n'a jamais
été ouverte pour cette task, sur aucun repo. `/merge` n'a donc pas d'objet — ce
n'est pas un garde-fou contournable, il n'y a matériellement rien à merger.

La branche existe pourtant et porte du travail réel :

```
feat/task-254-enrich-imap-fetch   4 commits d'avance, 5 de retard sur develop
  880d15c fix(loadtest)  — un tir qui franchit minuit ne perd plus son résumé
  4cf6021 perf(mail)     — une commande au lieu de deux pour le contenu d'un message
  0e71a35 docs(loadtest) — le décompte tranche : 3,23 allers-retours/message
  0b3f4e6 feat(telemetry)— compter les allers-retours IMAP d'un enrichissement
```

⚠️ Elle est **5 commits en retard** sur `develop` : task-251 (`b731306`),
task-252 (`e893fcd`) et task-249 (`db37379`) y ont atterri depuis. Un `git merge
origin/develop` sera nécessaire avant toute PR (jamais un rebase — règle 4).

## L'état réel de la US, et pourquoi ça compte

task-254 est une US **explicitement en deux étapes**, et son propre
`## Develop log` dit que seule la première est livrée :

> « **Reste à faire — étape 2/2** : Les 5 autres critères du DOD sont des
> optimisations et des mesures au banc. »

Décompte du DOD :

| Critère | État |
|---|---|
| Nombre d'allers-retours IMAP par message mesuré et rendu | ✅ livré (**3,23/message, dont 79 % de latence**) |
| Phase `fetch IMAP` réduite, **gain prouvé par A/B iso-conditions** | 🚧 un correctif existe (`4cf6021`) mais **l'A/B n'est pas fait** |
| Détention de `imap_session` mesurée avant/après | ❌ |
| Plateau de ~9,5 messages/s **franchi**, chiffre à l'appui | ❌ |
| Aucune régression : mêmes documents cliniques extraits (3 formes de corpus) | ❌ tests non écrits |
| Aucun message perdu ni dupliqué en cas d'échec partiel du lot | ❌ |

C'est aussi le cas visé par la **règle 11** du CLAUDE.md (US-complete merge
gate) : « aucune PR ne merge tant que la User Story complète n'est pas
fonctionnellement opérationnelle **et** validée humainement de bout en bout ».
Merger l'étape 1 seule poserait sur `develop` un correctif de performance
**dont le gain n'est pas prouvé** — exactement ce que le DOD exige de prouver.

## Ce que je n'ai pas fait

- Aucune PR mergée, aucune branche supprimée, aucun `develop` touché.
- La task reste en `wip-task-254.md`, dans l'état où elle était.
- La branche `feat/task-254-enrich-imap-fetch` est intacte (locale et distante).

## La décision qui vous revient

Trois voies, selon ce que vous voulez du travail déjà sur la branche :

1. **Finir l'étape 2/2** — reprendre la task (`/develop 254` ou à la main), faire
   l'A/B iso-conditions et les tests de non-régression, puis `/review 254` qui
   ouvrira la PR. C'est la voie conforme au DOD et à la règle 11.
2. **Découper** — si l'instrument (`0b3f4e6`, `0e71a35`) et le correctif de banc
   (`880d15c`) ont de la valeur **indépendamment** du gain de performance, en
   faire une US livrable à part : ils sont orthogonaux au reste et pourraient
   merger seuls. Le `perf(mail)` (`4cf6021`), lui, reste suspendu à son A/B.
3. **Merger quand même l'état actuel** — possible, mais c'est une dérogation
   explicite à la règle 11 : dites-le et je le fais (il faudra d'abord
   `git merge origin/develop`, puis `/review 254` pour ouvrir la PR).

⚠️ **Une réserve à ne pas perdre**, notée dans le task file : le chiffre de
3,23 allers-retours vient d'un instrument dont la mesure a **écarté** la piste
qu'on aurait corrigée d'abord (facteur 237). Toute reprise doit relire cette
section avant de choisir la piste — c'est précisément le service que
l'instrument a rendu.
