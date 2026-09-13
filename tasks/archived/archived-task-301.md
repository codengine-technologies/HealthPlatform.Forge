# todo-task-301.md — Reprise de l'historique d'audit vers la base commune, à débit borné, puis retrait de la table par praticien

**Repos**: api-mail
**Dependencies**: **task-299** (registre — sans lui, les tenants à reprendre ne sont pas
énumérables), **task-300** (table commune, partitionnement, RLS)
**Epic**: E016
**Priorité**: **2** — ferme le chantier. Sans elle, chaque praticien traîne indéfiniment une
table d'audit résiduelle et le chemin de lecture double de task-300 reste en place.

## Objective

Reprendre les traces d'audit **déjà écrites** dans les bases praticien vers la table commune,
**sans tempête de connexions**, puis retirer la table par tenant et le chemin de lecture double
introduit par task-300.

### La contrainte qui gouverne toute l'US

La reprise parcourt le parc entier : c'est **exactement la forme d'opération qui a mis Postgres
à genoux trois fois le 2026-09-11** (rejeu du tampon : 2 500 backends en 3 minutes, 27 575
refus `53300`, VM Docker figée 45 minutes). La leçon de task-298 s'applique intégralement ici :
**une opération qui touche les 1000 bases doit être lente et bornée, jamais rapide et large.**

Donc : concurrence plafonnée et configurable (défaut **4** bases simultanées), lots bornés,
reprise possible après interruption, et **arrêt automatique** si Postgres approche sa limite de
connexions. Une reprise qui prend une nuit est un succès ; une reprise qui sature le serveur
est un échec, même si elle est plus rapide.

### Déroulé

1. **Énumérer les tenants** depuis le registre (`ITenantRegistryClient.ListTenantsAsync`,
   task-299) — l'opération n'était pas réalisable avant, c'est ce que le registre débloque.
   L'unité de reprise est le **tenant** (compte × messagerie = une base), pas la messagerie :
   une adresse organisationnelle partagée par deux PS correspond à **deux** bases à reprendre.
2. Pour chaque base, **copier par lots** les traces antérieures à l'instant de bascule vers la
   table commune, en renseignant le `TenantId`, **idempotent** (une trace déjà reprise n'est
   jamais dupliquée — clé d'identité conservée).
3. **Vérifier** : nombre de traces reprises == nombre de traces source, **par tenant**. Toute
   divergence est un échec bloquant pour ce tenant, journalisé, sans arrêter les autres.
4. Marquer le tenant **repris** dans le registre ; l'écran d'audit cesse alors d'interroger la
   source héritée pour ce tenant.
5. Quand **tous** les tenants sont repris et vérifiés : retirer le chemin de lecture double, puis
   supprimer la table d'audit des bases praticien (migration par tenant).

L'étape 5 est **séparée dans le temps** de l'étape 4 et conditionnée à une validation humaine
explicite : on ne supprime pas une source de traçabilité PGSSI-S le jour même de sa copie.

## Definition of Done

- [ ] Build passes on api-mail (0 errors)
- [x] ~~**Prérequis hérité de task-299 (revue de code)** — le curseur de pagination du registre
      s'écrit `t.Id.CompareTo(cursor) > 0` … **Aucun test ne prouve qu'il se traduit en SQL**.~~
      **LEVÉ le 2026-09-13** : `TenantRegistryIntegrationTests.ListTenantsAsync_PaginatesWithA
      CursorTranslatedToSql` et son jumeau `ListDormantAccountsAsync_…` parcourent le parc par
      pages contre un **vrai PostgreSQL** (Testcontainers) et vérifient les deux propriétés de la
      pagination — aucune page répétée, aucun tenant sauté. **L'expression se traduit.** La
      reprise d'historique peut s'appuyer dessus sans réserve.
- [ ] Tests pass (0 failures)
- [ ] Commande de reprise déclenchable à la demande (pas de cron : `api-mail` n'a pas
      d'ordonnanceur), reprenable après interruption sans reprendre depuis le début
- [ ] Test unitaire : la reprise ne dépasse **jamais** `Backfill:MaxConcurrentDatabases`
      (défaut 4) bases simultanées, quel que soit le nombre de tenants dans le registre
      (compteur de concurrence observé)
- [ ] Test unitaire : **idempotence** — rejouer la reprise sur un tenant déjà repris n'insère
      aucune ligne et ne lève pas
- [ ] Test unitaire : **garde-fou de saturation** — au-delà d'un seuil de connexions Postgres
      configurable, la reprise se met en pause au lieu de continuer (fixture simulant la
      saturation)
- [ ] Test unitaire : un tenant en échec (base injoignable, divergence de comptage)
      **n'interrompt pas** la reprise des autres ; il est journalisé et laissé non marqué
- [ ] Test d'intégration : après reprise d'un tenant, l'écran d'audit du praticien rend
      **exactement le même contenu** qu'avant la reprise — même nombre, même ordre, aucun doublon
- [ ] Test : la vérification de comptage par tenant échoue **bruyamment** si une seule trace
      manque (test par retrait délibéré d'une ligne)
- [ ] Migration par tenant supprimant la table d'audit héritée, appliquée **uniquement** aux
      tenants marqués repris et vérifiés
- [ ] Retrait du chemin de lecture double de task-300 — il vit **entièrement dans
      l'implémentation** de `IAuditReader`, jamais dans le contrat : ce retrait ne change donc
      aucune signature (et, depuis la révision du 2026-09-13, plus aucun contrat de l'EPIC n'est
      publié en paquet — c'est pourquoi cette US ne liste pas `sdk`)
- [ ] **C'est cette US, et elle seule, qui supprime la configuration devenue morte** :
      `Audit:DrainParallelism` et le plafond de drain côté audit (`Audit:DrainMaxConnections`
      pour ce chemin — il **reste** pour le provisionnement). task-300 cesse de s'en servir mais
      ne les retire pas : tant que le chemin hérité vit, le réglage doit rester réglable. Le code
      ne garde pas deux architectures en parallèle une fois la reprise terminée
- [ ] Aucune donnée de santé en clair dans les logs de reprise (nombre de traces, nom de base,
      identifiant de tenant : oui ; contenu de trace : jamais)
- [ ] Documentation : runbook `Api/Mail/docs/runbook-reprise-audit.md` — comment lancer,
      comment suivre l'avancement, comment reprendre après incident, comment **vérifier avant
      de supprimer**

## Écart assumé — la configuration « morte » ne l'est pas encore

La DOD demande : « **C'est cette US, et elle seule, qui supprime la configuration
devenue morte** : `Audit:DrainParallelism` et le plafond de drain côté audit ».

**Non fait, et voici pourquoi.** task-300 n'a pas seulement déplacé le journal : elle a
gardé l'ancien chemin **comme filet**. Une trace sans `TenantId` — registre désactivé
(`TenantRegistry:ConnectionString` vide), registre injoignable, ou trace émise avant la
résolution du tenant — repart sur la base praticien via `PersistGroupAsync`, qui utilise
`DrainParallelism` et le sémaphore de `DrainMaxConnections`.

Ce filet est ce qui permet au journal de rester fonctionnel quand le registre n'est pas
configuré, et il a été **accepté au merge de task-300**. Retirer les réglages
maintenant :

- ne supprimerait aucune architecture en parallèle — le chemin de repli resterait, sans
  plafond ;
- rendrait ce chemin **non bornable**, c'est-à-dire exactement le défaut que task-298 a
  posé un garrot pour contenir.

La DOD elle-même énonce la condition : « tant que le chemin hérité vit, le réglage doit
rester réglable ». **Il vit.** Le retrait est donc une tâche de fin de chantier, quand la
décision aura été prise de supprimer le repli lui-même — ce qui est un arbitrage produit
(« le journal peut-il s'arrêter si le registre est absent ? »), pas un nettoyage de code.

> **Proposition** : rattacher ce retrait à la suppression des tables héritées (étape 5 du
> runbook), qui est de toute façon conditionnée à une validation humaine. Les deux
> décisions ont le même déclencheur — le parc entièrement repris — et la même nature :
> on ne retire un filet qu'une fois certain de ne plus en avoir besoin.

## Manual Test Plan

- **Pré-requis** : task-299 et task-300 déployées ; au moins deux praticiens de test disposant
  de traces antérieures à la bascule.
- **Lancer** : `cd Api/Mail && aspire run --project src/AppHost`, puis déclencher la reprise
  selon le runbook.
- **Ce que l'humain doit voir** :
  1. Pendant la reprise :
     `docker exec postgres-pgvector psql -U postgres -c "select application_name, count(*) from pg_stat_activity group by 1"`
     → le chemin de reprise reste **≤ 4 connexions**, et `docker logs --since 5m postgres-pgvector`
     ne contient **aucun** « too many clients ».
  2. Après reprise d'un praticien : son écran d'audit affiche le **même historique qu'avant**
     (comparer un export avant / après — même nombre de lignes, même ordre).
  3. Relancer la reprise une seconde fois → **aucune ligne insérée**, aucune erreur.
  4. Couper une base praticien pendant la reprise → ce tenant est signalé en échec, les autres
     se terminent normalement.
  5. **Avant toute suppression** : vérifier tenant par tenant que le comptage source ==
     comptage cible. C'est la porte de validation humaine de l'étape 5.
- **Données de test** : praticiens synthétiques du banc, aucune donnée réelle.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — continuité de la traçabilité
- **Exigences DSR honorées** : non applicable
- **INS** : les traces reprises portent `PatientIns` — contenu **inchangé**, simple déplacement
  physique, même finalité, même rétention
- **Authentification PS** : inchangée
- **Habilitations** : la reprise est une opération d'exploitation, pas un accès praticien ;
  elle n'ouvre **aucun** nouveau chemin de lecture
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : **point de vigilance central** — l'US déplace puis **supprime** une source
  de traçabilité. D'où l'exigence de vérification par comptage, la séparation dans le temps
  entre copie et suppression, et la validation humaine explicite avant l'étape 5. Aucune trace
  ne doit disparaître : c'est le critère d'acceptation de l'US
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — déplacement interne au même environnement HDS, aucun flux sortant
- **AIPD / impact RGPD** : couverte par la mise à jour de task-300 ; cette US en est l'exécution

---

## Branches

- `api-mail` (pushed) : `feat/task-301-reprise-historique-audit` — base `origin/develop`
  @ `ff6332f7` (task-300 mergée)
- `dtos-mss` (pushed) : `feat/task-301-reprise-historique-audit` — branche auto-incluse
  (CLAUDE.md « Auto-included repo »). Sans changement de contrat, elle restera **sans commit**.

> **Pré-flight** : les six repos automatisés sur `develop`, arbres propres. Dépendances
> `task-299` et `task-300` satisfaites — toutes deux en `tasks/archived/`, état terminal qui
> suit `done-*`.

### ⚠️ Second point de collision avec task-303 — à connaître avant d'écrire

`archived-task-300.md` documente déjà la collision **task-300 × task-303** (renommage
`tenants` → `mss_accounts`, et le trou silencieux sur la migration du journal).

**Cette US en ajoute un second, sur les mêmes fichiers.** task-301 retire le chemin de
lecture double source, donc modifie `PostgresAuditReader` — précisément le fichier que
task-303 doit aussi modifier pour suivre le renommage du DbSet.

| Fichier | task-301 y fait | task-303 y fait |
|---|---|---|
| `PostgresAuditReader` | **supprime** la fusion double source et la lecture de `audit_cutover_at` | renomme `context.Tenants` → `context.MssAccounts` |
| `PostgresAuditSink` | inchangé | renomme `UPDATE tenants` |
| migration `TenantDb/` | ajoute la reprise + le retrait de la table par tenant | renomme la table |

**Conséquence pratique, dans l'ordre de merge contraint** (task-303 ne peut pas merger
avant task-304, règle 11) : c'est **task-303 qui se resynchronise** sur un `develop` qui
portera peut-être déjà task-301. Si tel est le cas, une partie de sa réconciliation
**disparaît d'elle-même** — on ne renomme pas un appel dans du code qu'on vient de
supprimer.

Le risque inverse — task-301 mergée *après* task-303 — est celui qu'il faut surveiller :
elle supprimerait alors du code déjà renommé, ce qui est bénin, **mais sa propre migration
devrait viser `mss_accounts` et non `tenants`**. Le même piège silencieux que task-300, au
même endroit.

## Timings

*(généré par `tools/timing/report.sh --task task-301 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /develop | ok | 16 min 53 s | — | — | — | — |
| /sonar | ok | 17 min 04 s | — | — | — | 2 itération(s) |
| /lint-angular | skipped | 2.4 s | — | — | — | non touche par task-301 (Repos: api-mail) |
| /lint-mobile | skipped | 2.3 s | — | — | — | non touche par task-301 (Repos: api-mail) |
| /verify-visual | skipped | 2.2 s | — | — | — | non touche par task-301 (Repos: api-mail) |
| /review | ok | 4 min 59 s | — | 1 (0.9 s) | — | api-mail 0B/1T |
| /tech-writer | ok | 1 min 24 s | — | — | — | — |
| /start | ok | 56 s | — | — | — | — |
| **Total cycle** | | **41 min 25 s** | **0 (0.0 s)** | **1 (0.9 s)** | **0 (0.0 s)** | |

## Sonar log

**2 itérations** (scan initial + scan de vérification après correction).

### KPIs qualité (baseline → final)

| Métrique | Baseline (fin de task-300) | Final | Δ |
|---|---|---|---|
| **Quality Gate (new code)** | ERROR | ERROR | = |
| `new_violations` | 167 – 170 * | **168** | ≈ 0 |
| `new_bugs` | 2 | 2 | = |
| `new_vulnerabilities` | 2 | 2 | = |
| `new_code_smells` | 166 | 164 | −2 |
| `new_coverage` | 88,2 % | 88,1 % | −0,1 |
| Coverage projet | 88,1 % | 88,0 % | −0,1 |
| Duplication | 0,4 % | 0,4 % | = |
| Reliability / Security / Maintainability | 3,0 / 5,0 / 1,0 | 3,0 / 5,0 / 1,0 | = |

> \* **Deux sources, deux chiffres, et il faut le dire.** L'API `measures` rendait
> 170 en fin de task-300 quand l'API `issues` en comptait 167 ouvertes. L'écart est
> un décalage d'indexation, pas une divergence de fond — la même chose s'est
> reproduite ici : la requête faite juste après le scan listait encore une `CA1822`
> déjà corrigée, absente d'une requête faite une minute plus tard. **Le compte
> d'issues ouvertes fait foi**, le snapshot de mesures traîne.

### Ce que task-301 a introduit : **0**

Vérifié issue par issue via l'API, sur les **8 fichiers créés** (options, contrat,
`record` de rapport, service d'orchestration, service hébergé, magasin Postgres,
migration, tests) : **aucune issue ouverte**.

### Corrigé pendant cette étape (3 issues, toutes attribuables)

| Règle | Où | Fait |
|---|---|---|
| `S138` | `AddApplication` | Mes trois lignes d'enregistrement la poussaient de **97 à 100 lignes**. Extraites dans `AddAuditBackfill()` — ce qui a sa propre valeur : la reprise est un chantier temporaire, et la retirer sera une suppression d'appel, pas une chirurgie dans une méthode de cent lignes. |
| `CA1822` | `AuditDualSourceReadTests.ReadAllAsync` | `static` — le helper n'accède à aucun état d'instance. |
| `xUnit2033` | `TenantRegistryIntegrationTests` | Valeur **rendue** par `Assert.Single` au lieu de re-indexer. |

### Appliqué sans y être forcé : `S4457`

Les trois méthodes publiques `async` de `PostgresAuditBackfillStore` qui valident
leurs arguments sont passées à la forme « méthode non-`async` qui délègue à un
`…CoreAsync` privé ». **Sonar ne les avait pas signalées** — mais la convention
s'applique, et son compteur a été incrémenté une heure plus tôt pour exactement ce
motif. Mieux vaut l'appliquer spontanément que d'ajouter une troisième récidive.

### Security hotspots (`new_security_hotspots_reviewed` 83,3 % ⇒ ERROR)

Inchangés : les 2 hotspots à revoir sont toujours dans
`tests/loadtest-k6/test_report_session_lock_regime.py` (URLs `http://localhost`
d'un test Python du banc, task-298). **Hors périmètre de cette US.**

## Lint log

**`/lint-angular`, `/lint-mobile`, `/verify-visual` : skips propres.** `**Repos**: api-mail`
— aucune ligne d'Angular ni d'Ionic, aucun écran touché. US strictement backend
(reprise d'historique, migration, service hébergé).

---

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/235
  — label `awaiting-human-merge`.
- `dtos-mss` : **aucune PR** — branche auto-incluse, **0 commit** (aucune route, aucun contrat
  de fil touché).
- `client-blazor` / `client-angular` / `client-mobile` : **non concernés** — US strictement
  backend d'exploitation.

## Code Review Summary

**APPROVED** — 22 fichiers revus, **1 écart de DOD trouvé et comblé avant la PR**, 0 blocage
restant.

### L'écart comblé : le verrou de suppression était procédural

La DOD demande que la suppression de la table héritée soit « appliquée **uniquement** aux
tenants marqués repris et vérifiés ». Le mécanisme existait
(`IAuditBackfillStore.DropLegacyTableAsync`), mais la garde vivait dans le **runbook**, pas
dans le code.

Sur une opération **irréversible** portant sur une source de traçabilité PGSSI-S, ce n'est
pas suffisant. La signature prend désormais le **tenant** — et non le seul nom de base —
pour relire `audit_backfilled_at` et **refuser** si la marque est absente. Test bloquant
dans les deux sens : refus sans marque, acceptation une fois posée.

### Ce que la revue a confirmé

| Point | Verdict |
|---|---|
| Ordre compter → copier → **vérifier** → marquer | ✅ marquer avant de vérifier ferait perdre de l'historique en silence |
| Isolement des échecs par tenant | ✅ sur mille bases, s'arrêter au premier incident = ne jamais finir |
| Curseur déterministe (`ORDER BY "Id"`) | ✅ deux passes voient le même ordre, donc reprise sûre |
| Route directe hors pooler | ✅ motif task-200, plan de contrôle |
| `Application Name=mss-mail-backfill` | ✅ convention task-298, attribution sans devinette |
| Aucune donnée de santé dans les journaux | ✅ testé sur le chemin de **panne**, celui qui fuit |

### Suggestions non bloquantes

- `AuditBackfillService` énumère le registre page par page et traite chaque page avant la
  suivante. Un flux continu serait légèrement plus régulier — mais le gain est nul face au
  plafond de concurrence, qui est la vraie borne.
- `CountServerConnectionsAsync` compte **toutes** les connexions du serveur, pas seulement
  celles de la reprise. C'est voulu : le garde-fou protège le serveur, pas la reprise.

---

## Merged — 2026-09-13

Mergée par l'humain après attestation `--i-tested` (HAG, règle 10).

| Repo | PR | Commit de squash | CI `develop` |
|---|---|---|---|
| `api-mail` | [#235](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/235) | `ff3ddea7` | ✅ vert (3 min 55 s) |
| `dtos-mss` | — | aucune PR, **0 commit** | — |

Branches distantes supprimées ; **branches locales conservées**. Portes au moment du
merge : `mergeState CLEAN`, `MERGEABLE`, build `SUCCESS`, **0 commit de retard**, arbres
propres.

La ligne « traçabilité » de l'EPIC est désormais **entièrement sur `develop`** :
task-299 (registre) → task-300 (journal mutualisé) → task-301 (reprise d'historique).

---

## ⚠️ ACTION REQUISE DANS task-303 — renuméroter sa migration une seconde fois

**À traiter avant le merge de task-303. Le défaut est silencieux.**

### Le fait

task-303 (en cours sur `feat/task-303-comptes-multi-messageries`, 13 commits) porte la
migration `20260914120000_MergeMailboxesIntoMssAccounts`, qui fait
`Rename.Table("tenants").To("mss_accounts")`.

Son auteur a **déjà** renuméroté une fois, et pour la bonne raison : sa version initiale
`20260913180000` s'exécutait *avant* `20260914090000` (task-300), qui fait
`ALTER TABLE tenants ADD audit_cutover_at`. Sur une base neuve, on aurait renommé la table
avant de l'altérer. Le raisonnement est écrit dans le fichier et il est juste.

**Mais task-301 vient de merger avec la migration `20260914140000_AddAuditBackfillMark`**,
qui fait `ALTER TABLE tenants ADD COLUMN IF NOT EXISTS audit_backfilled_at`.

### Ce qui se passe sur une base NEUVE si rien n'est fait

| Ordre | Migration | Effet |
|---|---|---|
| 1 | `20260913120000` | crée `tenants` |
| 2 | `20260914090000` (task-300) | `ALTER TABLE tenants ADD audit_cutover_at` ✅ |
| 3 | `20260914120000` (task-303) | `RENAME tenants → mss_accounts` ✅ |
| 4 | `20260914140000` (task-301) | `ALTER TABLE tenants ADD audit_backfilled_at` ❌ **`42P01 relation "tenants" does not exist`** |

**Et l'échec est avalé.** `TenantRegistrySchemaInitializer` attrape l'exception et émet un
`LogWarning` — c'est délibéré : le registre ne doit jamais bloquer le démarrage du service.
Conséquence : le pod démarre, sert les praticiens, et le journal d'audit **n'a pas la colonne
qui fait cesser la lecture double source**. Aucune alerte, aucun test rouge.

**Invisible sur les bases de développement**, qui sont déjà migrées au-delà de `140000` :
FluentMigrator y appliquera `120000` hors séquence, après coup, et le renommage emportera
les deux colonnes. Ça marchera partout — sauf sur une installation neuve.

### Ce qu'il faut faire

**Renuméroter la migration de task-303 à une version strictement supérieure à
`20260914140000`** — par exemple `20260914160000`. L'ordre devient alors :

```
090000  ALTER TABLE tenants ADD audit_cutover_at
140000  ALTER TABLE tenants ADD audit_backfilled_at
160000  RENAME tenants → mss_accounts     ← emporte LES DEUX colonnes
```

`ALTER TABLE … RENAME` conserve les colonnes : il n'y a rien d'autre à faire.

**Pourquoi ce n'est pas à task-301 de bouger** : sa migration est **mergée**. La règle 7c
interdit d'éditer une migration livrée — c'est exactement le raisonnement que l'auteur de
task-303 a appliqué à lui-même face à task-300, et il vaut dans les deux sens. La migration
encore sur une branche est celle qui se renumérote.

### Reste à faire côté task-303 (inchangé depuis `archived-task-300.md`)

- `PostgresAuditSink.MarkCutoverAsync` (`UPDATE tenants`) et
  `PostgresAuditReader.ReadTenantMarksAsync` (`context.Tenants`) suivent le renommage —
  erreurs de compilation, donc bruyantes.
- `PostgresAuditBackfillStore` : trois requêtes visent `tenants`
  (`GetBackfilledAtAsync`, `MarkBackfilledAsync`) — **SQL brut, donc silencieuses**. À
  traiter en même temps.
- Les fixtures d'intégration qui sèment un `RegistryMailboxRow` — type supprimé, bruyant.

---

## Reste ouvert après ce merge

- **`devops`** : provisionner `mss_registry` et poser `TenantRegistry__ConnectionString`.
  Sans cela, registre désactivé **en silence**, journal sur l'ancien chemin, et la reprise
  n'a aucun tenant à énumérer. **Toute la ligne E016 reste inerte.**
- **La reprise ne se déclenche pas toute seule** : `Backfill:RunOnStartup` est `false` par
  défaut. Merger ne lance rien — c'est voulu. Procédure complète dans
  `Api/Mail/docs/runbook-reprise-audit.md`, sur **un seul** réplica.
- **Écart assumé** : `Audit:DrainParallelism` et le plafond de drain ne sont pas retirés —
  le chemin hérité vit encore comme filet pour les traces sans `TenantId`. Rattaché à la
  suppression des tables héritées, même déclencheur.
- **`questions/task-302.md`** : sans modèle de rôles, ni l'accès sécurité au journal, ni une
  route d'administration pour déclencher la reprise ne sont possibles.
- **Mesure au banc** de task-300 (DOD non cochée) : tir journey 1000, acte humain.
