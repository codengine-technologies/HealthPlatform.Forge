# todo-task-307.md — Rendre bruyantes trois requêtes silencieuses : passer en EF le SQL brut évitable du journal d'audit

**Repos**: api-mail
**Dependencies**: **task-301** (archivée — c'est elle qui a introduit deux des trois requêtes).
Aucune dépendance sortante : cette US ne bloque personne, mais elle **réduit le risque du merge
de task-303**, ce qui la rend urgente plutôt qu'importante.
**Epic**: E016
**Priorité**: **1** — la fenêtre se referme au merge de task-303. Après, le bénéfice principal
a disparu.

## Objective

Trois requêtes du journal d'audit mutualisé sont écrites en **SQL brut** alors que leur table a
une **entité EF mappée**. Les faire passer en EF, pour qu'un renommage de table casse à la
**compilation** au lieu de casser en production, en silence.

## Pourquoi cette US existe — le coût a déjà été constaté

Les tasks 299 → 301 ont introduit 18 requêtes en `NpgsqlCommand`. **La plupart n'avaient pas
d'alternative** : `ON CONFLICT DO NOTHING` par lot, `DELETE … LIMIT`, DDL de partition, RLS,
catalogues `pg_class` / `pg_stat_activity`, `SET LOCAL ROLE`. EF ne sait exprimer aucune de ces
choses, et le SQL brut y est la seule écriture possible.

**Trois ne sont pas dans ce cas.** Elles visent `tenants` et `audit_traces`, qui sont toutes deux
mappées dans `TenantRegistryDbContext` :

| Fichier | Requête | Entité disponible |
|---|---|---|
| `PostgresAuditBackfillStore.GetBackfilledAtAsync` | `SELECT audit_backfilled_at FROM tenants WHERE id = @id` | `Tenants` |
| `PostgresAuditBackfillStore.MarkBackfilledAsync` | `UPDATE tenants SET audit_backfilled_at = @at WHERE id = @id AND audit_backfilled_at IS NULL` | `Tenants` |
| `PostgresAuditBackfillStore.CountCommonAsync` | `SELECT count(*) FROM audit_traces WHERE tenant_id = @t AND timestamp < @before` | `AuditTraces` |

Elles ont été écrites en SQL brut **par cohérence avec le reste du fichier**, qui tient déjà sa
propre connexion pour les besoins ci-dessus. Le motif se défend en lecture ; il ne se défend pas
en coût.

### Le coût, constaté le jour même

task-303 renomme `tenants` en `mss_accounts`. Ces trois requêtes ne produiront **aucune erreur de
compilation** : elles échoueront à l'exécution, sur un `42P01`, et — pour deux d'entre elles —
dans un chemin d'arrière-plan dont l'échec est journalisé sans être propagé.

Il a fallu écrire un avertissement dans **trois endroits** (`archived-task-300.md`,
`done-task-303.md`, un commentaire sur la PR #236) pour qu'un renommage de table ne passe pas
inaperçu. **C'est le symptôme :** quand la seule protection contre une rupture est un paragraphe
de documentation, c'est que le code a cessé de se défendre lui-même.

En EF, `context.Tenants` devient `context.MssAccounts` et **le compilateur refuse de construire**.
Aucun avertissement à écrire, aucun à lire, aucun à oublier.

## Ce qui reste en SQL brut, et pourquoi

> ⚠️ **Cette US ne convertit PAS tout.** Elle vise exactement trois requêtes. Toute tentative
> d'en convertir davantage est hors périmètre et doit être refusée en revue.

| Reste en SQL brut | Raison |
|---|---|
| `PostgresAuditSink` — insertion groupée `ON CONFLICT` | pas d'upsert natif en EF, **et c'est le cœur du correctif de task-300** |
| `PostgresAuditSink.MarkCutoverAsync` — `UPDATE tenants` | doit vivre dans la **même transaction** que l'insertion du lot. Un `DbContext` séparé ouvrirait une seconde transaction, et la borne de bascule pourrait être posée alors que l'insertion échoue |
| `PostgresAuditJournalPurge` — `DELETE … LIMIT`, `DROP TABLE`, `pg_class` | ni bornage de `DELETE`, ni DDL, ni catalogue en EF |
| `PostgresAuditReader` — `SET LOCAL ROLE` + `set_config` | commandes de session |
| `PostgresAuditBackfillStore` — lecture de `MssAuditTraces` | base praticien désignée **par son nom**, hors de tout contexte utilisateur |
| `AuditPartitionMaintenance`, `MigrationHelper` | DDL et verrous consultatifs |

**`MarkCutoverAsync` est le cas intéressant** : il ressemble aux trois convertis — `UPDATE tenants`
sur une entité mappée — mais sa contrainte transactionnelle le rend non convertible. Il garde son
SQL brut **et son commentaire d'explication**, qui devient la référence pour distinguer les deux
situations.

## Fenêtre de tir

```
maintenant ────────────────────► merge de task-303 ───────────────────►
   task-307 : le renommage      │  task-307 : le renommage est déjà
   de 303 cassera bruyamment    │  fait — bénéfice principal perdu,
   à la compilation             │  reste la lisibilité
```

task-303 est en `done-*`, PR #236 **`awaiting-us-completion`** : elle attend task-304 (règle 11).
Il y a donc du temps — mais il est borné, et il se referme sans prévenir le jour où task-304 est
prête.

> **Si task-303 merge d'abord** : cette US reste valable, la conversion vise alors `MssAccounts`
> au lieu de `Tenants`, et son bénéfice se limite à la lisibilité. Le rapport bénéfice/coût
> s'effondre — à re-arbitrer plutôt qu'à exécuter par habitude.

## Definition of Done

- [ ] Build passes on `api-mail` (0 errors) ; tests pass (0 failures)
- [ ] `GetBackfilledAtAsync`, `MarkBackfilledAsync` et `CountCommonAsync` de
      `PostgresAuditBackfillStore` n'utilisent **plus** `NpgsqlCommand` — elles passent par
      `IDbContextFactory<TenantRegistryDbContext>`
- [ ] `MarkBackfilledAsync` conserve sa sémantique **« la marque ne recule jamais »** : mise à
      jour conditionnée à `audit_backfilled_at IS NULL`. Test existant conservé, et **un test
      explicite** vérifie qu'un second marquage ne déplace pas la valeur
- [ ] Le **verrou de suppression** (`DropLegacyTableAsync` refuse si le tenant n'est pas marqué)
      reste intact et son test bloquant reste vert — il s'appuie sur `GetBackfilledAtAsync`
- [ ] **Aucune régression de forme sur le chemin d'écriture** : `PostgresAuditSink` est
      **inchangé**. Un test d'architecture ou une revue vérifie que l'insertion groupée reste
      une instruction unique — c'est le correctif de capacité de task-300, il ne se dégrade pas
      par effet de bord
- [ ] Les 7 tests unitaires de `AuditBackfillServiceTests` et les 3 tests d'intégration du
      journal restent verts **sans modification de leurs assertions** : la conversion ne change
      aucun comportement observable
- [ ] Le pool du chemin de reprise reste borné et attribuable : le `DbContext` ajouté utilise la
      **même** chaîne que le reste du magasin (`Application Name=mss-mail-backfill`, pool borné à
      `MaxConcurrentDatabases`). Vérifié par test sur la chaîne construite
- [ ] **Commentaire de décision** sur `MarkCutoverAsync` expliquant pourquoi *lui* reste en SQL
      brut alors qu'il ressemble aux trois convertis — sans quoi la prochaine revue le
      convertira et cassera la transaction partagée
- [ ] `tasks/done-task-303.md` et la PR #236 mis à jour : les deux lignes « SQL brut, aucune
      erreur de compilation » de l'avertissement **disparaissent** de la liste, puisqu'elles
      n'ont plus lieu d'être

## Manual Test Plan

- **Lancer** : `cd Api/Mail && aspire run --project src/AppHost`
- **Actions et vérifications** :
  1. Se connecter avec un praticien de test, faire une action tracée, puis vérifier que la ligne
     `tenants.audit_cutover_at` est posée — **le chemin d'écriture n'a pas bougé**.
  2. Poser `Backfill:RunOnStartup=true` sur un réplica, redémarrer, et vérifier dans les journaux
     la ligne `[Backfill] Passe terminée — …`. **Même sortie qu'avant la conversion.**
  3. Relancer la reprise : **aucune ligne insérée**, et `audit_backfilled_at` **inchangé** (la
     marque ne recule pas).
  4. Vérifier l'attribution des connexions pendant la reprise :
     `docker exec postgres-pgvector psql -U postgres -c "select application_name, count(*) from pg_stat_activity group by 1"`
     → `mss-mail-backfill` reste **≤ 4**. Le `DbContext` ajouté ne doit pas créer un pool parallèle.
- **Le test qui prouve l'US** : renommer localement `TenantRegistryDbContext.Tenants` en
  `MssAccounts` et lancer le build. **Il doit échouer**, aux trois endroits convertis. Annuler
  ensuite le renommage — c'est une sonde, pas un changement.
- **Données de test** : praticiens synthétiques, aucune donnée réelle.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — dette technique sur le socle de traçabilité
- **Exigences DSR honorées** : non applicable
- **INS** : les requêtes converties ne lisent **aucune** donnée de santé — un horodatage, un
  identifiant de tenant, un comptage. Le contenu des traces n'est pas touché
- **Authentification PS** : inchangée
- **Habilitations** : inchangées — aucune nouvelle route, aucun nouveau chemin de lecture
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : **c'est l'objet de l'US, par la bande.** Deux des trois requêtes gouvernent
  la marque de reprise, qui commande à la fois la lecture double source **et** l'autorisation de
  supprimer une table d'audit. Une rupture silencieuse à cet endroit se solde par un journal
  incomplet à l'écran, ou par une suppression refusée à tort. Rendre la rupture bruyante est une
  mesure de **robustesse de la traçabilité**, pas un confort de développeur
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé — aucun flux, aucune donnée déplacée
- **AIPD / impact RGPD** : aucun — refactoring à comportement constant, couvert par les analyses
  de task-300 et task-301

## Ce que cette US n'est pas

- **Pas une conversion générale du SQL brut vers EF.** Quinze des dix-huit requêtes restent, et
  c'est justifié. Une US « supprimer le SQL brut » serait une régression : elle casserait
  l'insertion groupée, le bornage de la purge et le partitionnement.
- **Pas un durcissement de sécurité.** Un point adjacent a été relevé — `database_name` est
  interpolé dans une chaîne de connexion sans validation au point d'usage, sûr aujourd'hui par la
  seule provenance de l'appelant (`BuildUserDatabaseName`, assaini par construction). Il n'est
  **pas traité ici** : task-303 ajoute de nouveaux écrivains dans le registre
  (`AttachMailboxAsync`), donc la validation `^[a-z0-9_]+$` à l'écriture appartient à son
  périmètre. **À arbitrer avec elle**, pas à empiler ici.

## Timings

*(généré par `tools/timing/report.sh --task task-307 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | failed | 2 min 10 s | — | — | — | US sans objet — task-312 a supprime PostgresAuditBackfillStore et les 3 requetes visees |
| **Total cycle** | | **2 min 10 s** | **0 (0.0 s)** | **0 (0.0 s)** | **0 (0.0 s)** | |

---

## Abandonnée — sans objet (2026-09-16)

**Décision humaine du 2026-09-16, sur constat au pré-flight de `/start`.**
Aucune branche n'a été créée, aucun code n'a été écrit.

### Le sujet de la US a été supprimé

Les trois requêtes SQL brut à convertir vivaient dans
`PostgresAuditBackfillStore`. **Ce fichier n'existe plus.** `task-312` — commit
`b9400547`, PR #239, mergée — a retiré le journal d'audit hérité et toute sa
machinerie de reprise :

```
src/Infrastructure/Repositories/TenantDb/PostgresAuditBackfillStore.cs   ← les 3 requêtes
src/Application/Services/Repository/TenantDb/IAuditBackfillStore.cs
src/Application/Services/Implementation/AuditBackfillService.cs
src/Application/Services/Background/AuditBackfillHostedService.cs
src/Application/Configuration/AuditBackfillOptions.cs
src/Domain/Entities/TenantDb/AuditBackfillReport.cs
```

La colonne `audit_backfilled_at` a elle aussi été retirée de `mss_accounts` :
elle ne bornait que la double lecture, qui n'existe plus.

**Quatre des cinq critères du DOD** visent donc du code disparu
(`GetBackfilledAtAsync`, `MarkBackfilledAsync`, `CountCommonAsync`,
`DropLegacyTableAsync`, `MarkCutoverAsync`). Le cinquième — « `PostgresAuditSink`
inchangé » — est déjà satisfait.

### Aucun repli

Trois fichiers portent encore du `NpgsqlCommand` : `PostgresAuditSink`,
`PostgresAuditJournalPurge`, `PostgresAuditReader`. Ce sont **exactement** ceux
que cette US listait comme non convertibles, avec la consigne de refuser en
revue toute tentative d'élargir le périmètre. La seule surface convertible a
disparu.

### La US avait prévu une péremption, mais plus douce

Son encadré « Fenêtre de tir » annonçait qu'au merge de task-303 le bénéfice se
réduirait à la lisibilité — « à re-arbitrer plutôt qu'à exécuter par habitude ».
task-303 est effectivement mergée. Mais la réalité est allée plus loin : ce
n'est pas le bénéfice qui a disparu, c'est le sujet.

### Ce qui survit à l'abandon

Le **principe** reste juste : une requête SQL brut sur une table qui a une
entité EF perd la protection du compilateur, et un renommage casse alors en
production au lieu de casser au build. Il n'a plus de cible aujourd'hui, mais il
en aura une au prochain accès direct — d'où la suggestion de le verser dans
`conventions/csharp.md` plutôt que de le laisser mourir avec cette US.
**Non fait à ce stade** : hors du geste d'archivage demandé.

Analyse complète : `questions/task-307.md`.
