# questions/merge-task-074.md — PR #97 en conflit avec develop

**Task** : `tasks/done-task-074-caching-applicatif-settings-referentiels.md` (reste en `done-*`)
**Étape bloquée** : `/merge task-074 --i-tested` — gate 5 (branch vs develop)
**Date** : 2026-06-11

## Le problème

La PR [#97](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/97)
est `CONFLICTING/DIRTY` vis-à-vis de `develop`. Les squash-merges du jour ont
fait diverger la base depuis l'ouverture de la PR :

- task-070 (`3e4deb4`) et task-071 (`4d88f3e`) ont modifié
  `src/Infrastructure/Repository/PatientRepository.cs` — que task-074 modifie
  aussi (cache patient par INS). C'est le foyer de conflit le plus probable.
- task-072 (`3bf6dce`) et task-073 (`bac7b1b`) ont touché la DI/Program — chevauchement possible.

Aucune PR n'a été mergée par ce run (`/merge` est atomique). Gates par
ailleurs verts : label `awaiting-human-merge`, CI build pass, review vierge.

## État des autres PRs au moment du constat

| PR | Task | Mergeabilité |
|----|------|--------------|
| #98 | task-075 | ✅ MERGEABLE/CLEAN (débloque task-076) |
| #99 | task-077 | ✅ MERGEABLE/CLEAN |
| #97 | task-074 | ❌ CONFLICTING/DIRTY |
| #91 | task-079 | ⏳ UNKNOWN (GitHub recalcule) |
| #92 | task-080 | ⏳ UNKNOWN (GitHub recalcule) |

## Pour débloquer

1. Résoudre le conflit sur la branche (merge, jamais rebase — règle 4) :
   ```bash
   cd Api/Mail
   git checkout feat/task-074-caching-settings-referentiels
   git fetch origin develop
   git merge origin/develop        # résoudre les conflits (PatientRepository.cs attendu)
   dotnet build HealthPlatform.Api.Mail.sln && dotnet test HealthPlatform.Api.Mail.sln
   git push
   git checkout develop
   ```
2. Relancer `/merge task-074 --i-tested`.

Alternative : merger d'abord #98/#99 (CLEAN) via `/merge task-075|task-077 --i-tested`,
puis résoudre #97 une seule fois contre le develop final.

## ✅ Résolution (2026-06-11)

Conflit résolu par la forge à la demande du humain : merge `origin/develop`
dans la branche (commit `1080878`), conflit limité au bloc `using` de
`PatientRepository.cs` (Helpers 074 + Models 071 — les deux conservés),
build Release 0 erreur, suites vertes (hors flaky pré-existants), CI PR
verte, puis squash-merge `5da065d`. Question close.
