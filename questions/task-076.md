# questions/task-076.md — Séquencement : attendre le merge de task-075 (PR #98)

**Task** : `tasks/todo-task-076-sync-background-parallelisation.md` (laissée en `todo-*`, non démarrée)
**Étape bloquée** : pré-`/start` — dépendance de séquencement
**Date** : 2026-06-10 (run /forge)

## Le problème

La task déclare `**Dependencies**: todo-task-075 (… à implémenter d'abord pour
éviter les conflits sur les mêmes fichiers)`. task-075 est bien `done-*`
(PR [#98](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/98),
`awaiting-human-merge`), **mais pas encore mergée sur `develop`** (HAG, règle 10).

Or task-076 réécrit précisément les zones modifiées par task-075 :
- `BackgroundImapService.RemoveMissingUidsAsync` (075 : signature + token ; 076 : delete batch)
- `MailClientSessionManager` (075 : ctor sans Task.Run, hosted cleanup ; 076 : remplacement du sémaphore global)
- `BackgroundSyncService` / `BackgroundSyncManager` (075 : file gérée + tokens ; 076 : concurrence bornée)

Brancher task-076 depuis `develop` (sans les commits de #98) produirait des
conflits de merge majeurs et invaliderait la revue de l'une des deux PRs. La
forge ne pratique pas les PRs empilées (squash-merge en aval les casse).

## Pour débloquer

1. Tester et merger task-075 : `/merge task-075 --i-tested` (après les autres PRs en attente si souhaité).
2. Relancer `/start task-076` (ou `/forge` — la task est restée en `todo-*`).

Aucune décision métier à prendre — pur séquencement HAG.

## ✅ Résolution (2026-06-11)

task-075 (PR #98) squash-mergée sur `develop` (`230ea24`, CI verte) via
`/merge task-075 --i-tested`. Le blocage de séquencement est levé —
`/start task-076` peut être relancé (les repos forge sont sur `develop`).
