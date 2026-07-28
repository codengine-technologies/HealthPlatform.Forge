# todo-task-200.md — PgBouncer mode transaction devant Postgres : lever le plafond de connexions de l'architecture « une base par praticien »

**Repos**: api-mail
**Dependencies**: —
**Epic**: E015
**Single frontend**: true

> **Origine** : campagne de charge 200 praticiens du 2026-07-27. Le plafond est
> **mesuré**, pas théorique, et la limite est déjà documentée dans le code
> (`BaseRepository.DefaultMaxPoolSize`) : « keep (practitioners served per pod)
> × (this value) under the server's max_connections, **or front Postgres with a
> transaction-mode pooler** ». Cette task est le spike qui valide ce pooler.
> Dimensionnement cible : `DevOps/DIMENSIONNEMENT-1000-PRATICIENS.md`.

## Objective

Valider (ou invalider, avec preuves) que **PgBouncer en mode transaction** peut
porter l'architecture « une base Postgres par praticien » au-delà du plafond
mesuré, et livrer la brique intégrée au **profil loadtest de l'AppHost** pour
que le tir 500 praticiens devienne possible.

Le plafond actuel est structurel : `connexions retenues ≈ praticiens ×
réplicas × Max Pool Size`. Le palier 200 × 5 réplicas n'est passé qu'en force
brute (Postgres 12 GiB, `max_connections=2500`) — mesuré : ~2 000 connexions
retenues stables. À 1000 praticiens ce serait 10 000+ : un backend Postgres
par connexion ne passe pas à l'échelle. PgBouncer multiplexe ces connexions
sur quelques centaines de backends réels.

**US backend/bench-only (justification)** : infrastructure de connexion et
profil loadtest de l'AppHost — aucun contrat, aucun écran.

### Preuve du plafond (campagne du 2026-07-27)

- `Max Pool Size=4` : rafale d'ouverture des 1 000 pools froids ≈ 3 000
  connexions en 15 s → **OOM-kill du postmaster** (`terminated by signal 9`)
  sur un conteneur à 4 GiB.
- `max_connections=800` : `53300: sorry, too many clients already` en masse.
- `Connection Idle Lifetime=15` : recyclage continu des pools → **~200 000
  SocketException 10048** (ports éphémères épuisés) en 5 min.
- Configuration verte finale (200 praticiens) : Max=2 / Idle=600 /
  `max_connections=2500` / 12 GiB — 915 req/s, 0,02 % d'erreurs. C'est une
  transition, pas une cible : la RAM Postgres croît linéairement avec les
  praticiens provisionnés, même inactifs.

### Contenu attendu

1. **Points de compatibilité à trancher un par un** (c'est le cœur du spike) :
   - Npgsql en mode transaction : `Max Auto Prepare=0`, `No Reset On Close=true`,
     absence de `SET` de session sur le chemin de requête — inventorier le code
     (`BaseRepository`, repositories, `NpgsqlDataSource` + `UseVector()`).
   - **pgvector** : l'enregistrement du type via `dataSourceBuilder.UseVector()`
     survit-il au multiplexage transaction ? (Le handshake de types se fait par
     connexion physique.)
   - **FluentMigrator / provisionnement** (`UpdateDatabase`, advisory locks
     `pg_advisory_xact_lock`) : les locks transactionnels passent en mode
     transaction, mais `CREATE DATABASE` et les migrations doivent passer **en
     direct sur Postgres**, pas via PgBouncer — câbler `ConnectionStringServer`
     en conséquence.
   - `LISTEN/NOTIFY` ou toute dépendance à l'état de session : inventaire et
     verdict.
2. **Intégration au profil loadtest** : conteneur PgBouncer dans l'AppHost
   (profil `loadtest` uniquement), configuré par base dynamique
   (`auth_query` ou `*` dans `[databases]`), `pool_mode=transaction`,
   `default_pool_size=2`, `max_db_connections=3`, `server_idle_timeout=60`,
   `max_client_conn` dimensionné. Chaîne api-mail pointée sur PgBouncer,
   **`ConnectionStringServer` (provisionnement) pointée sur Postgres direct**.
3. **Mesure comparative** : re-tir `mixed` 200 praticiens **iso-conditions**
   via PgBouncer — mêmes KPIs (rapport `report.sh`, ligne INDEX). Critère :
   pas de dégradation p95 > 20 % vs le run de référence
   `report-mixed-mssante-60vu-003515.md`, backends Postgres réels < 300.
4. **Verdict documenté** : courte ADR (compatible / compatible avec réserves /
   incompatible et pourquoi), consignée dans `Api/Mail/docs/`, référencée
   depuis `DevOps/DIMENSIONNEMENT-1000-PRATICIENS.md` §4.

### Hors scope

- Le tir 500 praticiens lui-même (task suivante, une fois cette brique verte).
- Le déploiement PgBouncer en Staging/Prod (équipe système —
  `DIMENSIONNEMENT-1000-PRATICIENS.md`).
- Les corrections sync-over-async de `BaseRepository` (task séparée).

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] Test d'intégration : requête EF Core standard (lecture `Mails`) via
      PgBouncer mode transaction — verte
- [ ] Test d'intégration : opération **pgvector** (insertion + similarité)
      via PgBouncer mode transaction — verte
- [ ] Test d'intégration : provisionnement d'une base praticien neuve
      (advisory lock + `CREATE DATABASE` + `MigrateUp`) avec PgBouncer en
      place — vert (chemin direct Postgres)
- [ ] Profil loadtest AppHost : PgBouncer démarre avec le banc, api-mail s'y
      connecte, `SHOW POOLS` accessible pour le diagnostic
- [ ] Tir `mixed` 200 praticiens via PgBouncer : mêmes seuils k6 PASS que le
      run de référence, backends Postgres réels < 300 (`pg_stat_activity`)
- [ ] Rapport de tir généré (`report.sh` + ligne INDEX) et comparé au run de
      référence dans l'ADR
- [ ] ADR de compatibilité écrite dans `Api/Mail/docs/` et liée depuis
      `DevOps/DIMENSIONNEMENT-1000-PRATICIENS.md`
- [ ] Hors profil loadtest, **aucun changement de comportement** (PgBouncer
      absent = chemin actuel inchangé, vérifié par la suite de tests existante)

## Manual Test Plan

1. Monter le banc avec le profil loadtest (cf. skill `loadtest-skill`) —
   PgBouncer doit apparaître dans les ressources Aspire.
2. Vérifier le pooler : `docker exec <pgbouncer> psql -p 6432 -U pgbouncer
   pgbouncer -c 'SHOW POOLS'` → pools par base praticien, mode transaction.
3. Seeder 200 × 100 puis tirer :
   `USERS=200 MESSAGES_PER_USER=100 tests/loadtest-k6/run.sh mixed --env VUS=60 --env DURATION=5m`.
4. Pendant le tir : `select count(*) from pg_stat_activity` sur Postgres
   **direct** → doit rester < 300 (contre ~2 000 sans pooler).
5. Comparer la ligne INDEX du rapport au run de référence du 2026-07-27 :
   p95 par opération dans la marge de 20 %.
6. Lire l'ADR : verdict et réserves compréhensibles sans avoir suivi la task.

## Branches

- `api-mail` (pushed) : `feat/task-200-pgbouncer-transaction-pooling` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-200-pgbouncer-transaction-pooling
- `dtos-mss` (pushed, auto-inclus) : `feat/task-200-pgbouncer-transaction-pooling` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-200-pgbouncer-transaction-pooling

### Pre-flight (2026-07-27)

Tous les repos forge présents sont sur `develop`, aucun sur une branche de
feature. Deux écarts d'environnement relevés, non bloquants (hors cibles de
cette task) :

- `client-mobile` — `Client/Mobile/` **absent du disque** (repo non cloné ;
  `Client/` ne contient que `Blazor`). Idem `client-angular`. Une task listant
  ces repos échouerait à `/develop`.
- `host` — `Host/Modules/` n'est **pas un repo git autonome** : il appartient
  au repo racine `D:/TechWatch/HealthPlatform`. À noter, le workspace racine
  **est** un dépôt git (remote `HealthPlatform.Forge`, branche `develop`), alors
  que le CLAUDE.md le décrit comme « NEVER pushed — it has no remote ».

## Develop log

- **Repos touched** : `api-mail` uniquement. `dtos-mss` : branche créée par
  `/start`, **aucun commit** — pas de changement de contrat (US infra), donc
  aucune PR à ouvrir et aucun publish NuGet.
- **DTOs published** : no DTO change. **Interop published** : no interop change.
- **Commits** (`api-mail`, `feat/task-200-pgbouncer-transaction-pooling`, poussés) :
  - `94a9416` feat(db): route provisioning work directly to Postgres, off the transaction pooler
  - `5b9ade3` feat(loadtest): front the bench Postgres with PgBouncer in transaction mode
  - `5a71fa6` test(db): prove PgBouncer transaction-mode compatibility end to end
  - `bb3664d` docs(db): ADR on PgBouncer transaction mode — compatible with two reservations
- **Local build / test** : build 0 erreur / 0 warning ; suite complète
  **3 140 tests verts, 0 échec**, 16 skips préexistants (tests IA nécessitant
  des clés API). Détail : domain 102, infrastructure 370, api 573,
  application 1829, integration 266. Aucun flaky rencontré (la fenêtre de
  minuit de `PatientRepositoryTests` n'était pas active).
  Le seul changement postérieur à ce run est un refactor de `const` dans
  l'AppHost (projet sans tests), re-validé par build.

### Ce que le spike a tranché (verdicts, pas déductions de lecture)

Sondes manuelles d'abord (paire Postgres/PgBouncer isolée), puis figées en tests
d'intégration qui montent **la configuration réelle du banc** :

| Point de la task | Verdict |
|---|---|
| EF Core / Npgsql à travers le pooler | compatible |
| **pgvector** (`UseVector`, insertion + similarité) | **compatible** — l'OID du type est stable par base, et Npgsql tient un DataSource par base |
| Provisionnement (verrou consultatif, `CREATE DATABASE`, `MigrateUp`) | basculé sur la **route directe** ; exercé via le code de production `BaseRepository.CreateDbContextAsync` |
| Multiplexage effectif | **confirmé** : 40 clients simultanés → **≤ 3 backends** Postgres mesurés dans `pg_stat_activity` |
| `LISTEN`/`NOTIFY` | non concerné — aucun usage dans api-mail (Redis pub/sub + RabbitMQ) |
| `SET` de session sur le chemin de requête | absent — seul `SET LOCAL lock_timeout`, transactionnel et sur la route directe |
| Réserves | `Max Auto Prepare=0` et `No Reset On Close=true` sont des invariants côté Npgsql (ADR §4) |

**Finding non anticipé par la task** — `host.docker.internal` ne résout qu'en
**AAAA** dans le conteneur PgBouncer, et PgBouncer (contrairement à `psql`) ne
retente pas sur l'autre famille d'adresses : toute connexion cliente meurt en
`client_login_timeout (server down)` alors que le TCP est accepté et que
`SHOW POOLS` répond. Un banc qui démarre « sain » et ne sert rien. Troisième
occurrence du même piège IPv6 Docker Desktop dans ce banc. Corrigé par
`--add-host=pgupstream:host-gateway` (IPv4 déterministe) et **verrouillé par un
test garde-fou**, un commentaire n'ayant manifestement pas suffi les deux fois
précédentes. La configuration réelle du banc a été vérifiée à la main contre le
Postgres du banc après correctif (207 bases visibles à travers le pooler).

### DOD self-check

Vérifiés par commande (8/11) :

- [x] Build 0 erreur — [x] Tests 0 échec
- [x] Test d'intégration EF Core via PgBouncer
- [x] Test d'intégration pgvector via PgBouncer
- [x] Test d'intégration provisionnement (route directe, pooler debout)
- [x] Hors profil loadtest, aucun changement de comportement — la variable
      directe n'est **pas définie** hors banc et le repli est couvert par test
      unitaire ; chaîne de connexion hors banc identique à l'octet près
- [x] ADR écrite dans `Api/Mail/docs/`
- [x] ADR liée depuis `DevOps/DIMENSIONNEMENT-1000-PRATICIENS.md` §4 —
      **voir la réserve ci-dessous**

Différés au banc / HAG (3/11) — non bloquants pour `/develop`, ce sont des
observations de charge :

- [ ] Profil loadtest : PgBouncer démarre avec le banc, `SHOW POOLS` accessible.
      Le conteneur, la configuration, l'upstream et la commande `SHOW POOLS` ont
      été validés **à la main** contre le Postgres du banc ; ce qui reste non
      vérifié est le **démarrage de l'AppHost Aspire lui-même** (résolution du
      bind mount relatif, publication du port 6432, passage des runtime args).
      C'est l'étape 1 du Manual Test Plan.
- [ ] Tir `mixed` 200 praticiens via PgBouncer : seuils k6 PASS, backends < 300
- [ ] Rapport de tir généré et comparé au run de référence dans l'ADR

L'ADR est explicite sur ce point (§6 « Ce que cette ADR ne prouve pas ») : la
compatibilité fonctionnelle est établie, la **tenue en charge comparative ne
l'est pas encore**. Le prérequis §4.1 du document de dimensionnement n'est donc
pas encore levé et l'ADR le dit.

### ⚠️ Réserve — modification non committée dans un repo exclu

Le lien vers l'ADR exigé par la DOD touche `DevOps/`, qui est un **repo git
autonome et entièrement exclu de l'automation forge** (CLAUDE.md). Le fichier
`DevOps/DIMENSIONNEMENT-1000-PRATICIENS.md` §4.1 est donc **modifié mais laissé
non committé**, sur le modèle du mode code-only : la forge écrit, l'humain
commit et pousse. Diff prêt à relire dans WindSurf.

### Note d'outillage

`conventions/csharp.md` (lu par `/develop` avant tout code C#, cf. CLAUDE.md
« Conventions apprises ») **n'existe pas** — le répertoire `conventions/` est
absent du workspace. Les règles appliquées sont celles de
`Api/Mail/.github/instructions/dotnet-coding-rules.instructions.md`, référencées
par le CLAUDE.md du repo.

- Next step : /forge-simplify task-200

## Simplify log

- **Repos passed** : `api-mail` (seul repo touché — 14 fichiers de diff vs
  `develop`).
- **Skipped (contract/exclus)** : `dtos-mss` (porteur de contrat, et sans diff
  de toute façon), `interop-cda`, `devops`, `psc-proxy-*`.
- **Applied & committed** : `api-mail`, 5 fichiers — `61c8632`
  `refactor(db): simplify pass (/simplify) — task-200` (poussé).

Cleanups appliqués, par axe :

| Axe | Cleanup |
|---|---|
| Réutilisation | le test de provisionnement vérifiait l'existence de la base avec son propre SQL → passe par `MigrationHelper.DatabaseExists`, **le helper de production** que `BaseRepository` utilise pour décider du `CREATE DATABASE`. Le test gagne en fidélité au passage. |
| Réutilisation | la remontée vers la racine du repo (pour monter la configuration réelle du banc) était dupliquée entre la fixture PgBouncer et les smoke tests Dovecot de task-195 → extraite dans `BenchConfigLocator`, les deux y passent. |
| Efficacité | le sampler de backends ouvrait une connexion neuve toutes les 25 ms, **sur la base même qu'il comptait** → une seule connexion de mesure longue durée : la sonde ne perturbe plus sa propre mesure et ne paie plus un handshake par échantillon. |
| Simplification | le test de rafale rapiéçait sa chaîne de connexion par un `Replace` fragile → la fixture prend `maxPoolSize` en paramètre. |
| Simplification | `RequestHelper.EnsureConnectionString` répétait deux fois le même bloc « lire l'env si non renseigné » → un helper nommé. |

- **Écarté** : `EnsureConnectionString` duplique toujours la logique de
  résolution du middleware. Le fix profond (un point de résolution unique)
  remodèle un design préexistant bien au-delà du diff de cette task
  (règle 6, scopes isolés) — noté, pas fait.
- **Build / tests** : build 0 erreur / 0 warning ; suite complète **3 140 tests
  verts, 0 échec** avant et après la passe (16 skips IA préexistants). Aucun
  rollback nécessaire.
- **Écart de procédure** : le playbook `/simplify` prévoit 4 agents de revue en
  parallèle via l'Agent tool. La consigne de session interdit d'appeler l'Agent
  tool sans demande explicite de l'humain — la revue sur les 4 axes (réutilisation,
  simplification, efficacité, altitude) a donc été faite en direct sur le diff.
- Next step : /sonar task-200 (api-mail touché)

## Sonar log

Mode A (chaîné), 2 itérations sur la branche de la task. Serveur SonarQube
9.9.8, projet `healthplatform-api-mail`.

| KPI | Baseline (develop) | Final (scan 2) | Cible new-code |
|---|---|---|---|
| Quality Gate | OK | **OK** | OK ✅ |
| Bugs / New bugs | 0 / 0 | **0 / 0** | 0 ✅ |
| Vulnérabilités / New | 0 / 0 | **0 / 0** | 0 ✅ |
| New code smells | 6 | **6** | 0 ⚠️ (voir note) |
| Code smells (projet) | 31 | **31** | — |
| Coverage / New coverage | 86,0 % / 87,5 % | **86,5 % / 87,6 %** | ≥95 ⚠️ (voir note) |
| Maintainability | A | **A** | A ✅ |
| Security hotspots | 3 | 3 | — |

- **Périmètre task-200 : 0 smell restant.** Le scan 1 avait fait apparaître
  **1** issue imputable à la task (`CA1822` sur `PgBouncerFixture.DatabaseName`)
  et **1** warning d'analyseur (`S2068`, littéral `Password=postgres` dupliqué
  par mon refactor de l'AppHost). Les deux sont corrigés
  (`ce487b4`) : `new_code_smells` et `code_smells` sont revenus **exactement à
  la baseline**, et la couverture a monté (86,0 → 86,5 ; new 87,5 → 87,6).
- **Les 6 new-code smells restantes ne viennent pas de cette task** — ce sont
  les mêmes 6 que task-199 avait déjà imputées à des tasks mergées
  antérieurement (période new-code large) : `BackgroundSyncService` S107,
  `OcspValidationService` S3604+S1168, `MailClientSession` S3604×2,
  `VCardSerializer` S1643. Aucun fichier touché par task-200. Hors périmètre
  (règle 6, scopes isolés) — candidats à un run standalone `/sonar api-mail`
  (Mode B).
- **New coverage 87,6 % < 95** : même cause, la période new-code couvre du code
  d'autres tasks. Le code de task-200 est couvert par 17 tests dédiés
  (8 domaine, 4 api, 5 intégration).
- **Tests** : suite complète verte aux deux scans (3 140 passés, 0 échec,
  16 skips IA).
- **Outillage — piège rencontré** : lancé depuis Git Bash, `dotnet sonarscanner`
  ne reçoit pas ses arguments MSBuild-style (`/k:`, `/d:`) — MSYS les prend pour
  des chemins Unix et les réécrit en chemins Windows, si bien que le scanner se
  plaint de l'absence de clé de projet. Le skill `sonar-skill` est écrit en
  PowerShell et n'a pas ce problème. Contournement :
  `MSYS_NO_PATHCONV=1` + `MSYS2_ARG_CONV_EXCL='*'`. À consigner dans le skill si
  la forge continue à tourner en bash.
- **`conventions/csharp.md` créé** (il n'existait pas, cf. la note d'outillage du
  Develop log) avec les deux règles corrigées à la main — CA1822 et S2068 — pour
  que `/develop` les applique d'emblée. La boucle d'auto-amélioration décrite
  dans le CLAUDE.md est donc amorcée côté C#.
- Itérations : 2/5. Next : /review task-200 (`lint-angular`, `lint-mobile`,
  `verify-visual` : skip — repos non touchés).

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/125
  — label `awaiting-human-merge`
- `dtos-mss` : aucun changement de contrat — branche sans commit, **pas de PR**
  (build validé : 0 erreur)
- `client-angular` / `client-mobile` : non listés dans `**Repos**:`, non touchés
  (et non clonés sur cette machine — cf. Pre-flight)
- `DevOps` : repo **exclu de l'automation**. Le lien vers l'ADR exigé par la DOD
  est écrit dans `DIMENSIONNEMENT-1000-PRATICIENS.md` §4.1 mais **laissé non
  committé** — managed manually by the human.

## Code Review Summary

**APPROVED** — 16 fichiers relus, **0 issue bloquante**, 3 suggestions non
bloquantes (recopiées dans le body de la PR) :

1. `RequestHelper.EnsureConnectionString` duplique la logique de résolution du
   middleware (motif préexistant, une ligne de plus ici). Fix profond hors du
   diff de la task (règle 6).
2. `Provisioning_TakesDirectRoute_…` modifie `ASPNETCORE_ENVIRONMENT` au niveau
   processus (restauré en `finally`). Sûr **parce que** `xunit.runner.json`
   impose `maxParallelThreads=1` ; fragile si le parallélisme est activé un jour.
   Le fix propre exige d'abstraire la lecture d'environnement dans
   `BaseRepository` — hors scope.
3. `userlist.txt` porte des identifiants de banc en clair et le conteneur publie
   6432 sur `0.0.0.0`. **Pas une régression** : le Postgres du banc publie déjà
   5432 avec les mêmes identifiants, donc aucune capacité nouvelle. Corpus 100 %
   synthétique, aucune donnée de santé.

Vérifications de non-régression conduites pendant la revue : le repli de
`FromEnvironmentIfUnset` est sémantiquement identique à l'ancien code dans les
trois cas (valeur déjà posée / variable absente / variable présente) ; les
`NpgsqlDataSource` sont mis en cache par chaîne de connexion, donc les deux
routes ne peuvent pas se télescoper ; `GetOrCreateDataSource` est appelé avant
le provisionnement mais la création d'un DataSource Npgsql est paresseuse, ce
que le test d'intégration exerce de bout en bout.

**Réserve de méthode** : la revue est faite par la forge sur son propre code.
Les deux points qui méritent le plus l'œil humain sont le split des deux chemins
dans `BaseRepository.UpdateDatabase` et l'invariant « hors profil loadtest, rien
ne change ».

Validation : build 0 erreur / 0 warning ; **3 140 tests verts, 0 échec**
(16 skips IA préexistants) ; Sonar Quality Gate OK, 0 smell sur le périmètre.

## Merged

**Date** : 2026-07-27 11:51 UTC — `/merge task-200 --i-tested` (attestation
humaine du Manual Test Plan, HAG règle 10).

| Repo | PR | Squash commit sur `develop` |
|---|---|---|
| `api-mail` | [#125](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/125) (closed) | `179eb32280f34c390e9303d87d57b241060b9076` |
| `dtos-mss` | aucune PR (branche sans commit) | — |

- **Branches** : refs distantes `feat/task-200-pgbouncer-transaction-pooling`
  supprimées sur `api-mail` et `dtos-mss` ; **branche locale conservée** sur
  `api-mail` pour inspection rétroactive. Les deux clones sont revenus sur
  `develop`.
- **CI `develop` (api-mail)** : run
  [30263527572](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/30263527572)
  — **success** (`build` + `publish` verts), confirmé dans la fenêtre de 2 min
  de la règle 5.
- **Staging** : aucune branche `forge/staging-task-*` sur `api-mail` ni
  `dtos-mss` (task lancée hors run `/forge` groupé) — rien à nettoyer.
- **Reste à la main de l'humain** : `DevOps/DIMENSIONNEMENT-1000-PRATICIENS.md`
  §4.1 (lien vers l'ADR) — modification **toujours non committée** dans un repo
  exclu de l'automation. Voir la réserve du Develop log.
- **Reste ouvert après ce merge** (consigné dans l'ADR §6) : les 3 items de DOD
  différés au banc — démarrage PgBouncer via l'AppHost Aspire, tir `mixed` 200
  praticiens à travers le pooler, rapport comparatif. Le prérequis §4.1 du
  document de dimensionnement n'est donc **pas levé** par ce merge.
