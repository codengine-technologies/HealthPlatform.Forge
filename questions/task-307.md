# questions/task-307.md — la US n'a plus d'objet

> Écrit le 2026-09-16, au pré-flight de `/start task-307`.
> **Aucune branche n'a été créée, aucun code n'a été écrit.** La chaîne s'est
> arrêtée avant, et c'est un fail-fast (règle 7), pas un refus de travailler.

## Le constat

task-307 demandait de convertir en EF **trois requêtes SQL brut** de
`PostgresAuditBackfillStore` :

| Méthode visée | Requête |
|---|---|
| `GetBackfilledAtAsync` | `SELECT audit_backfilled_at FROM tenants WHERE id = @id` |
| `MarkBackfilledAsync` | `UPDATE tenants SET audit_backfilled_at = … WHERE …` |
| `CountCommonAsync` | `SELECT count(*) FROM audit_traces WHERE …` |

**Ces trois méthodes n'existent plus. Le fichier qui les portait non plus.**

`task-312` — commit `b9400547`, PR #239, **mergée** — a retiré le journal
d'audit hérité et toute sa machinerie de reprise, dont :

```
src/Infrastructure/Repositories/TenantDb/PostgresAuditBackfillStore.cs   ← les 3 requêtes
src/Application/Services/Repository/TenantDb/IAuditBackfillStore.cs
src/Application/Services/Implementation/AuditBackfillService.cs
src/Application/Services/Background/AuditBackfillHostedService.cs
src/Application/Configuration/AuditBackfillOptions.cs
src/Domain/Entities/TenantDb/AuditBackfillReport.cs
tests/…/Services/Audit/AuditBackfillServiceTests.cs
```

La colonne `audit_backfilled_at` elle-même a été retirée de `mss_accounts` par
la migration de task-312 : elle ne bornait que la double lecture, qui n'existe
plus.

## Quatre des cinq critères du DOD visent du code disparu

| Critère du DOD | État sur `develop` |
|---|---|
| Les 3 méthodes passent par `IDbContextFactory` | **sans objet** — supprimées |
| `MarkBackfilledAsync` garde « la marque ne recule jamais » | **sans objet** — supprimée |
| Le verrou `DropLegacyTableAsync` reste intact | **sans objet** — supprimé |
| `MarkCutoverAsync` garde son SQL brut comme cas de référence | **sans objet** — supprimé |
| `PostgresAuditSink` inchangé | seul critère encore applicable — et il est **déjà** satisfait, personne n'y a touché |

## La US avait prévu sa propre péremption — mais pas celle-ci

Le task file porte cet encadré :

> **Si task-303 merge d'abord** : cette US reste valable, la conversion vise
> alors `MssAccounts` au lieu de `Tenants`, et son bénéfice se limite à la
> lisibilité. Le rapport bénéfice/coût s'effondre — **à re-arbitrer plutôt
> qu'à exécuter par habitude.**

task-303 **est** mergée (`archived-task-303.md`), donc cette clause s'applique
déjà. Mais la situation réelle va plus loin que ce que le PO avait anticipé :
ce n'est pas le *bénéfice* qui a disparu, c'est le *sujet*. Il n'y a plus rien
à convertir.

## Ce qui reste en SQL brut est exactement ce que la US interdisait de toucher

Trois fichiers utilisent encore `NpgsqlCommand` :

- `PostgresAuditSink` — insertion groupée `ON CONFLICT` (cœur du correctif de
  capacité de task-300)
- `PostgresAuditJournalPurge` — `DELETE … LIMIT`, DDL, `pg_class`
- `PostgresAuditReader` — `SET LOCAL ROLE`, `set_config`

Ce sont **précisément** les trois que task-307 listait dans sa table
« Reste en SQL brut, et pourquoi », avec l'avertissement :

> ⚠️ Cette US ne convertit PAS tout. Elle vise exactement trois requêtes. Toute
> tentative d'en convertir davantage est hors périmètre et doit être refusée en
> revue.

**Il n'y a donc aucun repli** : la seule surface convertible a été supprimée, et
ce qui subsiste est explicitement hors périmètre par décision du PO.

## ❓ Décision demandée

**Archiver task-307 comme sans objet** — c'est ma recommandation, et le geste
est le même que pour task-306 le 2026-09-15 : déplacement dans
`tasks/archived/`, avec une note disant que task-312 a supprimé son sujet.

Deux réserves, pour que la décision soit éclairée :

1. **Le principe de la US, lui, reste juste** : une requête SQL brut sur une
   table qui a une entité EF perd la protection du compilateur, et un
   renommage casse alors en production au lieu de casser au build. Ce principe
   mériterait une note dans `conventions/csharp.md` plutôt qu'une US — il n'a
   plus de cible aujourd'hui, mais il en aura une au prochain accès direct.

2. **Rien ne presse plus.** La « fenêtre de tir » décrite dans le task file
   s'est refermée deux fois : au merge de task-303 (le renommage), puis à celui
   de task-312 (la suppression). Il n'y a aucun coût à laisser la décision
   attendre.

## Ce que je n'ai pas fait, et pourquoi

Je n'ai **pas** créé les branches et je n'ai **pas** enchaîné sur `/develop`.
Créer une branche sur `api-mail` pour une US dont les cinq critères sont sans
objet aurait produit une PR vide ou, pire, une conversion improvisée sur du code
que la US demandait explicitement de ne pas toucher.

Le pré-flight lui-même était vert : les cinq repos automatisés sont sur
`develop` et propres.
