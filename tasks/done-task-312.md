# todo-task-312.md — Retirer le journal d'audit hérité de la base praticien, et tout ce qui n'existait que pour en sortir

**Repos**: api-mail
**Dependencies**: **task-300** (journal mutualisé, mergée), **task-301** (reprise
d'historique, mergée), **task-308** (mergée — elle a déjà supprimé les lignes
`mss_accounts` non validées, donc les marques de bascule qu'elles portaient).
Aucune dépendance sortante.
**Epic**: E016
**Priorité**: **1** — décision humaine du 2026-09-14 : il n'y a **aucune donnée de
production**, donc rien à décommissionner avec précaution. Ce qui reste est de la dette
pure : une table morte, une double lecture permanente, et une machinerie de migration qui
n'a plus de destination.

## Objective

Supprimer la table d'audit de la base praticien (`MssAuditTraces`) et **tout ce qui
n'existait que pour en sortir** : son dépôt, sa purge, la lecture double source, la
machinerie de reprise et ses deux marques.

Après cette US, le journal d'audit a **une seule source** : `audit_traces`, en base
commune.

## Le point de départ : ce que « les entités qui s'y rattachent » recouvre vraiment

> ⚠️ **`MssAuditTrace` n'est PAS l'entité de la table héritée, et elle reste.**
>
> C'est la **monnaie de toute la chaîne d'audit**, journal mutualisé compris :
> `IAuditService.Trace(actionType, Action<MssAuditTrace>)`. Chaque appel `_audit.Trace(…)`
> du produit configure un `MssAuditTrace` ; le drain les met en lot, Redis les déverse en
> débordement, et ils sont convertis en `AuditTraceRecord` pour la base commune.
> **305 occurrences dans 54 fichiers.** Retirer ce type éventrerait le système d'audit
> entier — c'est l'inverse du but.
>
> Ce qui part, c'est ce qui est attaché **à la table**.

## Ce qui est supprimé

| Pièce | Fichier | Rôle |
|---|---|---|
| Table `MssAuditTraces` + 2 index | `Migrations/MailDb/20240101_SetupMigration.cs:587` | le magasin hérité |
| Mapping EF | `Persistance/MailDataContext.cs` | le `DbSet` |
| `AuditTraceRepository` / `IAuditTraceRepository` | `Repositories/MailDb/`, `Services/Repository/` | seul écrivain et lecteur de la table |
| Jambe héritée du lecteur | `PostgresAuditReader.cs:79` et `:94` | la lecture double source |
| Purge de rétention héritée | `AuditBackgroundService.cs:~228-285` | purge **cette** table, et s'y journalise |
| `AuditBackfillService` + `IAuditBackfillService` | `Services/Implementation/` | reprise d'historique |
| `IAuditBackfillStore` + `PostgresAuditBackfillStore` | `Services/Repository/TenantDb/`, `Repositories/TenantDb/` | dont `DropLegacyTableAsync`, **sans appelant de production** |
| `AuditBackfillHostedService` + `AuditBackfillOptions` | `Services/Background/`, `Configuration/` | déclencheur `Backfill:RunOnStartup`, **jamais activé** |
| Marques `audit_cutover_at` / `audit_backfilled_at` | `mss_accounts` | elles ne bornaient que la double lecture → **migration `TenantDb` nouvelle** |
| Repli du contrôleur | `AuditController.cs:64` et `:82` | `TenantId is null ? legacy : commun` |

Plus une quinzaine de fichiers de test.

## ⛔ Le blocage que cette US fait apparaître — à traiter DANS l'US

**La purge de rétention du journal mutualisé n'est branchée nulle part.**

- `IAuditJournalPurge` / `PostgresAuditJournalPurge` sont **enregistrés en DI**
  (`Infrastructure/Extensions/ServiceCollectionExtensions.cs:129`) et **n'ont aucun
  appelant**.
- La **seule** purge qui s'exécute aujourd'hui est celle du drain, et elle porte sur la
  table **héritée** (`repository.PurgeOlderThanAsync`, `AuditBackgroundService:~241`).

Donc, en l'état : **supprimer la table héritée supprimerait la seule purge de rétention
qui tourne**. Le journal mutualisé — celui qui porte INS, nom de patient, sujet et
expéditeur — croîtrait indéfiniment, sans effacement à échéance. Ce serait remplacer une
dette technique par un manquement RGPD.

> La documentation de `IAuditJournalPurge` le dit déjà, et c'est ce qui rend l'omission
> visible : *« la purge était opportuniste, déclenchée par l'activité du tenant lui-même.
> Un tenant dormant ne déclenchait plus jamais de purge, et ses traces — porteuses d'INS
> et de nom de patient — … »*. Le remède a été écrit ; il n'a jamais été branché.

**Cette US branche donc la purge de la base commune** avant de retirer l'héritée. Ce n'est
pas un élargissement de périmètre : c'est la condition pour que le retrait soit légal.

## Ce que le retrait ferme par ailleurs

- **Plus de décommissionnement à orchestrer.** `DropLegacyTableAsync`, sa garde sur la
  marque de reprise, le runbook « une nuit, sous surveillance, tenant par tenant » :
  sans table, le sujet disparaît.
- **Plus de lecture double source.** Chaque consultation d'audit interrogeait deux
  sources, indéfiniment, puisque la marque n'était jamais posée. Le coût cesse.
- **Le 10 % manquant de la traçabilité** dans `Docs/epics/E016-*.md` disparaît **par
  suppression du problème**, pas par exécution d'un runbook.

## Definition of Done

### La purge d'abord — sans elle, rien ne se retire

- [x] `IAuditJournalPurge` est **branché** et s'exécute réellement : service hébergé,
      cadence configurable, arrêt propre. Un test prouve qu'une trace plus ancienne que
      sa rétention est supprimée de `audit_traces`
- [x] Les **deux familles de rétention** sont respectées (`HealthDataAccessDays` vs
      `TechnicalDays`) — c'est la distinction PGSSI-S, pas un réglage
- [x] **La purge se journalise elle-même**, comme le faisait l'héritée : c'est la seule
      suppression autorisée pendant la rétention, elle doit dire ce qu'elle a retiré et
      jusqu'à quelle borne
- [x] La purge est **bornée par lot** (`PurgeBatchSize`) : une purge non bornée sur une
      table d'un milliard de lignes bloque la base

### Le retrait

- [x] Table `MssAuditTraces` et ses deux index retirés de
      `20240101_SetupMigration.cs` — **la migration ne les crée plus**. Aucune base neuve
      ne porte cette table
- [x] `DbSet` retiré de `MailDataContext` ; `AuditTraceRepository` et
      `IAuditTraceRepository` **supprimés**
- [x] `PostgresAuditReader` ne lit plus qu'**une** source. Sa signature ne prend plus de
      dépôt hérité
- [x] `AuditController` ne porte plus de repli : un `TenantId` nul rend un résultat
      **vide**, pas une lecture d'une autre source. Test explicite
- [x] Toute la machinerie de reprise supprimée : `AuditBackfillService`,
      `IAuditBackfillService`, `IAuditBackfillStore`, `PostgresAuditBackfillStore`,
      `AuditBackfillHostedService`, `AuditBackfillOptions`, et leur enregistrement DI.
      **Vérification binaire** : `grep -rn "Backfill" Api/Mail/src` → 1 résultat,
      un faux positif : `NewMailNotifier.cs:136` commente un « backfill guard » de
      synchronisation de courrier, sans aucun rapport avec la reprise d'audit
- [x] Migration `TenantDb` **nouvelle** (règle 7c) retirant `audit_cutover_at` et
      `audit_backfilled_at` de `mss_accounts`. Elles ne bornaient que la double lecture
- [x] Les entités et le `DbContext` du registre ne portent plus ces deux colonnes ; la
      liste blanche de colonnes de `TenantRegistryArchitectureTests` et du test
      d'intégration est mise à jour
- [x] `Backfill:RunOnStartup` retiré de toute configuration et documentation

### Ce qui ne doit pas bouger

- [x] **`MssAuditTrace` reste** — c'est le type de la chaîne, pas celui de la table. Les
      305 usages ne sont pas touchés
- [x] Le drain continue d'écrire en base commune par lot, en **une seule instruction** :
      c'est le correctif de capacité de task-300, il ne se dégrade pas par effet de bord.
      Un test d'architecture ou une revue le vérifie
- [x] Le **débordement Redis** (`RedisAuditSpillStore`) est inchangé : il porte des
      `MssAuditTrace`, pas la table
- [x] La RLS, les deux rôles et le partitionnement d'`audit_traces` sont inchangés ;
      leurs tests d'intégration restent verts sans modification d'assertion

### Transverse

- [x] Build passes (0 erreur) ; tests : **3 960 verts**, **5 rouges** —
      `…Today…` (×5), **échecs pré-existants** et sans rapport avec ce diff.
      **Vérifié, pas supposé** : les mêmes 5 échouent sur `origin/develop` nu
      (worktree détaché, même poste, même minute). Voir `## Develop log`
- [x] Les tests qui couvraient la table héritée sont **supprimés**, jamais commentés ni
      mis en `Skip` — un test qui survit au code qu'il décrit devient une affirmation sur
      du vide

## Manual Test Plan

- **Lancer** : `cd Api/Mail && aspire run --project src/AppHost`
- **Actions et vérifications** :
  1. **Base praticien neuve** : se connecter avec un praticien de test, faire une action
     tracée, puis
     `docker exec postgres-pgvector psql -U postgres -d {base_praticien} -c "\dt"` →
     **aucune table `MssAuditTraces`**.
  2. **La trace est en base commune** :
     `docker exec postgres-pgvector psql -U postgres -d mss_registry -c "select count(*), count(distinct tenant_id) from audit_traces;"`
     → compte non nul.
  3. **L'écran d'audit fonctionne** : ouvrir le journal dans l'interface → les traces
     s'affichent, mono-source, sans erreur.
  4. **La purge tourne** : abaisser temporairement la rétention technique à 0 jour,
     attendre un cycle, vérifier que les traces techniques ont disparu d'`audit_traces`
     **et** qu'une trace `AuditPurge` a été écrite disant combien et jusqu'à quelle borne.
  5. **Contrôle du registre** :
     `docker exec postgres-pgvector psql -U postgres -d mss_registry -c "\d mss_accounts"`
     → **plus de `audit_cutover_at` ni `audit_backfilled_at`**.
  6. **Contre-épreuve** : `grep -rn "Backfill\|MssAuditTraces" Api/Mail/src` → **aucun
     résultat**.
- **Données de test** : praticien synthétique, aucune donnée de santé réelle.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — dette technique sur le socle de traçabilité
- **Exigences DSR honorées** : non applicable
- **INS** : aucune donnée de santé lue ni écrite par le retrait lui-même. Mais les traces
  du journal **portent** INS, nom de patient, sujet et expéditeur — d'où l'exigence de
  purge ci-dessous, non négociable
- **Authentification PS** : inchangée
- **Habilitations** : inchangées. La RLS et les deux rôles du journal mutualisé ne sont
  pas touchés — c'est eux qui tiennent l'isolation entre praticiens
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : **c'est le cœur de l'US, et dans les deux sens.**
  - *Au crédit* : le journal passe à **une seule source**. La lecture double source, qui
    ne devait être que transitoire, était devenue permanente faute de reprise exécutée —
    et un journal probant lu depuis deux endroits est un journal dont l'exactitude dépend
    d'une borne que personne ne pose.
  - *Au débit, et c'est bloquant* : la **seule purge de rétention qui s'exécute** porte
    aujourd'hui sur la table héritée. La retirer sans brancher celle de la base commune
    laisserait un journal porteur d'INS croître **sans effacement à échéance**. L'US
    branche donc la purge mutualisée **avant** de retirer l'héritée, et le DOD le place
    en premier item
  - Durées de conservation inchangées : 3 653 jours pour les accès aux données de santé,
    la durée technique pour le reste
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé — aucun flux, aucune donnée déplacée. Une table est
  supprimée d'un schéma, pas exportée
- **AIPD / impact RGPD** : **favorable, à condition que la purge soit branchée.** Une
  copie des traces disparaît (la base praticien), et l'effacement à échéance devient
  effectif sur la copie restante — alors qu'il ne l'était sur aucune des deux pour un
  tenant dormant

### DOD santé applicable

- [x] Aucune donnée de santé en clair dans les journaux applicatifs (INS, NIR, contenu
      CDA, contenu MSSanté) — inchangé, à re-vérifier sur le code touché
- [x] Évènements PGSSI-S journalisés : `AuditPurge` est **conservée**, émise par la purge
      mutualisée, avec le nombre supprimé et la borne
- [x] La rétention est **effectivement appliquée** au journal mutualisé — prouvé par test,
      pas seulement enregistré en DI

## Ce que cette US n'est pas

- **Pas la suppression de `MssAuditTrace`.** C'est le type de la chaîne d'audit, pas celui
  de la table. Il reste, avec ses 305 usages.
- **Pas un décommissionnement progressif.** Décision humaine du 2026-09-14 : aucune donnée
  de production, donc ni runbook, ni reprise, ni vérification tenant par tenant. On retire.
- **Pas une refonte du journal mutualisé.** Partitionnement, RLS, deux rôles, insertion
  groupée, débordement Redis : tout est inchangé.
- **Pas l'occasion de revoir les durées de rétention.** Elles sont reprises telles quelles.
  Les discuter est un sujet de conformité, pas de dette technique.

## Branches

Créées par `/start 312` le 2026-09-14, depuis `origin/develop`. Préfixe `chore/` — l'US
retire de la dette, elle n'apporte aucune fonctionnalité.

- `api-mail` (pushed) : `chore/task-312-retrait-audit-herite`
  https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/chore/task-312-retrait-audit-herite
- `dtos-mss` (pushed, auto-incluse) : `chore/task-312-retrait-audit-herite`
  https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/chore/task-312-retrait-audit-herite

> Pré-vol : `api-mail`, `client-blazor`, `client-mobile`, `dtos-mss`, `sdk` tous sur
> `develop`, arbres propres. `host` et `interop-cda` n'ont pas de dépôt sur ce poste.
> Dépendances task-300, task-301 et task-308 toutes archivées.

## Develop log

> `/develop 312`, reprise le 2026-09-15 après résolution de `questions/task-312.md`.

### Ce que le retrait a fait apparaître, et qui n'était pas dans l'US

Trois choses que seul le retrait pouvait révéler — chacune corrigée dans cette US
parce qu'elles sont des **conséquences directes** de la suppression, pas du périmètre
ajouté :

1. **Le compteur de tentatives ne s'incrémentait plus.** `TransportAttempts` était
   incrémenté dans la persistance trace-à-trace de la base praticien, retirée ici.
   Sans le geste, il serait resté à 0 : le budget poison n'aurait jamais été atteint
   et une trace qu'aucune insertion ne peut accepter serait revenue au tampon
   **indéfiniment**. Réinstallé dans `ParkFailedTraceAsync`, le point unique où une
   trace en échec passe désormais.

2. **La borne de bascule n'avait plus de lecteur.** `audit_cutover_at` était posée à
   **chaque lot**, par un `RESET ROLE` plus un `UPDATE` par tenant, dans la
   transaction d'écriture. Son seul consommateur était la lecture double source,
   supprimée par cette US. Retirée avec les deux colonnes.

3. **Deux réglages ne réglaient plus rien.** `Audit:DrainParallelism` et
   `Audit:DrainMaxConnections` bornaient le nombre de **bases praticien** drainées
   simultanément. Il n'y a plus qu'une base. Retirés : un réglage qui ne règle rien
   invite à le tourner.

### Ce qui a été supprimé et non remplacé

- `docs/runbook-reprise-audit.md` — le mode opératoire d'une opération qui n'existe
  plus. L'ADR du journal mutualisé porte désormais la décision (§5 réécrit : la
  transition prévue n'a pas eu lieu, l'état final est atteint par suppression).

### Tests : adaptés plutôt que supprimés, sauf quand le sujet disparaît

| Fichier | Sort | Pourquoi |
|---|---|---|
| `AuditBackgroundServiceBatchingTests` | **adapté** | mesure toujours « combien d'écritures pour N traces » ; l'assertion « deux groupes » s'**inverse** en « un seul lot » — c'était la forme du défaut corrigé par task-300 |
| `AuditBackgroundServiceFallbackTests` | **adapté** | tampon, budget poison, charge utile : invariants task-292, intacts. Les deux tests de concurrence par groupe praticien partent avec leur sujet |
| `AuditBackgroundServiceReplayAndPurgeTests` | **scindé** | renommé `…ReplayTests` ; la purge n'est plus une branche du drain, ses tests suivent la purge dans `AuditRetentionHostedServiceTests` |
| `AuditDirectRouteIntegrationTests` | **supprimé** | tout le fichier portait sur la route directe vers la table héritée |
| `CrossTenantOwnershipTests` (section audit) | **supprimé** | l'isolation ne se joue plus en C# mais en RLS Postgres — et `AuditJournalIntegrationTests` la vérifie là où elle s'applique, avec un cas de plus que l'ancien couple ne savait pas voir (deux PS sur la même adresse organisationnelle) |
| `AuditRetentionHostedServiceTests` | **créé** | 7 cas : partitions avant lots, borne par famille, verrou légal sur les deux chemins, passe à vide muette, `SET NX` et marqueur pris, absence de Redis, puits en panne |

### Rouge pré-existant, hors diff

Cinq tests d'intégration IMAP (`…Today…`) échouent : le corpus date ses messages
relativement au jour du semis et le filtre `SINCE` ne les retrouve pas. **Ils
échouent à l'identique sur `origin/develop`** — vérifié dans un worktree détaché,
même poste, même minute, pendant ce cycle. Ni causés ni aggravés par cette US.
Ils méritent leur propre task.

### Volume

45 fichiers, **+1 106 / −4 795**. Au-dessus du repère de ~30 fichiers de la règle 5,
et assumé : 15 de ces fichiers sont des **suppressions**, et l'arbitrage humain du
2026-09-14 (« tout faire d'un coup ») a écarté le découpage — un retrait à moitié ne
compile pas, donc ne se merge pas.

## Sonar log

2 itérations, `api-mail`, `healthplatform-api-mail`. **Phase 1 (new code) verte**,
Phase 2 (dette héritée) **arrêtée volontairement** — motif ci-dessous.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| **Quality Gate (new code)** | OK | **OK** | = |
| New coverage | 83,0 % | **84,8 %** | +1,8 pt |
| New bugs / vulnérabilités | 0 / 0 | **0 / 0** | = |
| New code smells | 40 | **35** | −5 |
| Bugs / Vulnérabilités / Smells (projet) | 0 / 0 / 233 | **0 / 0 / 228** | −5 smells |
| Coverage projet | 87,4 % | **87,7 %** | +0,3 pt |
| Duplication | 0,4 % | **0,4 %** | = |
| Ratings (fiabilité / sécurité / maintenabilité) | A / A / A | **A / A / A** | = |

### Ce que Sonar a trouvé, et qui n'était pas cosmétique

**Les 5 findings de cette task étaient tous des vestiges du retrait** — c'est
précisément ce qu'on attend d'un scan après une suppression. Quatre étaient du
code mort ; le cinquième était une **régression fonctionnelle** :

> `S1172 — Remove this unused method parameter 'sortBy'`

Le paramètre n'était pas « inutilisé par négligence » : la **seule**
implémentation qui l'honorait était celle de la base praticien. En retirant cette
source, l'API a continué d'**accepter** `sortBy` en l'**ignorant** — l'écran
d'audit aurait gardé des en-têtes de colonne qui ne trient plus rien, **sans la
moindre erreur**. Le tri a été rapatrié à l'identique (six champs triables, même
défaut) et couvert par `AuditReaderSortIntegrationTests` (4 cas, base dédiée).

Les quatre autres : `CloneWithWindow` (S1144, dernier vestige de la fenêtre de
fusion), un commentaire scindé pris pour du code mort (S125), un jeton
d'annulation inutilisable (S1172), et un second paramètre de tri.

### Phase 2 arrêtée après 0 itération — assumé

Les 34 findings restants sont **tous dans des fichiers que cette US ne touche
pas** (`ITenantRegistryClient` ×14 CA1068, `BaseRepository`,
`TenantRegistryExceptions`, fixtures de test), hérités de task-299/303. Les
corriger ici élargirait le diff d'une US de retrait à des fichiers sans rapport,
pour ~7 min de passes de couverture par itération. La baseline projet est déjà
aux cibles dures (`bugs=0`, `vulnerabilities=0`, `sqale=A`).

Le seul `CRITICAL` restant est **S3776** sur `PostgresTenantRegistryClient:443` —
**blacklisté** (`agents/sonar-blacklist.yml`), traité par `/sonar-s3776`, une
méthode par PR.

### Outillage : le port de SonarQube a encore changé

`agents/sonar.md` affirmait « 9001 ». Mesuré ce jour : `docker port sonarqube`
rend `9000/tcp -> 0.0.0.0:9000`, et 9001 ne répond pas. **Troisième correction en
six semaines** — l'encadré a donc été réécrit pour ne plus graver *aucune*
valeur, seulement la procédure de contrôle et `$SONAR_HOST_URL`.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/239
  — label `awaiting-human-merge`
- `dtos-mss` : **aucune PR** — la branche auto-incluse n'a reçu aucun commit (le
  retrait ne touche aucun contrat partagé). `/merge` la supprimera (étape 5 bis).

## Code Review Summary

**APPROVED** — 46 fichiers, 3 suggestions, 0 bloquant.

La revue a trouvé **trois commentaires orphelins** laissés par le retrait — un
commentaire de section sans ligne en dessous, un commentaire `task-301` devenu
l'en-tête d'un enregistrement DI sans rapport, une ligne vide double. Corrigés
(commit `35586b9`) : un commentaire qui survit au code qu'il décrit désigne la
mauvaise ligne.

Trois suggestions non bloquantes, laissées telles quelles et documentées dans le
corps de la PR :

1. `SystemTenantId = Guid.Empty` défini dans deux fichiers avec deux
   justifications distinctes — le factoriser créerait une dépendance entre deux
   services qui n'en ont aucune.
2. Une base de dev **existante** garde sa table `MssAuditTraces` orpheline : la
   migration ne la crée plus, mais aucun `Delete.Table` n'a été ajouté. Sans
   conséquence — la table n'est plus ni lue ni écrite.
3. L'édition d'une migration **mergée** est contraire à la règle 7c. Assumée sur
   décision humaine du 2026-09-14.

## Timings

*(généré par `tools/timing/report.sh --task task-312 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 24 s | — | — | — | — |
| /develop | ok | — | 15 (1 min 00 s) | 2 (3 min 06 s) | — | api-mail 15B/2T, no start marker |
| /sonar | ok | 19 min 27 s | 4 (38 s) | 10 (6 min 28 s) | — | 2 itération(s), api-mail 4B/10T |
| /lint-angular | skipped | 0.4 s | — | — | — | client-angular non touche (Repos: api-mail) |
| /lint-mobile | skipped | 0.5 s | — | — | — | client-mobile non touche (Repos: api-mail) |
| /verify-visual | skipped | 0.4 s | — | — | — | aucun ecran mobile touche |
| /review | ok | 4 min 17 s | 2 (8.4 s) | 1 (1 min 32 s) | — | api-mail 2B/1T |
| /tech-writer | ok | 4 min 55 s | — | — | — | — |
| **Total cycle** | | **29 min 06 s** | **21 (1 min 47 s)** | **13 (11 min 07 s)** | **0 (0.0 s)** | |
