# todo-task-202.md — Libérer les connexions de la route de provisionnement : ~1 backend Postgres retenu par praticien, pour rien

**Repos**: api-mail
**Dependencies**: task-200 (mergée — c'est elle qui a introduit la route directe)
**Epic**: E015
**Single frontend**: true
**Priorité**: **3/6** — Plafond population (ordre arrêté le 2026-07-31, objectif montée en charge)
> ~1 backend Postgres retenu PAR PRATICIEN, definitivement. La regle de dimensionnement du palier 1000 est `praticiens x repliques x pool` : c'est exactement ce plafond-la. Aucun correctif de debit ne le deplace.

> **Origine** : campagne 200 et 500 praticiens du 2026-07-27, premiers tirs à
> travers PgBouncer. Le pooler fait son travail (2 000 connexions clientes →
> 400 backends), mais **la moitié des backends restants ne lui appartient pas**.
> Rapports : `Api/Mail/tests/loadtest-k6/reports/2026-07-27/report-mixed-mssante-60vu-144525.md`
> (tir A) et `…-150vu-141351.md` (tir 500).

## Objective

Faire en sorte que la **route directe de provisionnement** (verrou consultatif,
`CREATE DATABASE`, `MigrateUp`) ne retienne **aucune connexion Postgres** une
fois la base d'un praticien migrée. Aujourd'hui elle en garde **une par base**,
pendant 5 minutes, alors qu'elle ne resservira plus de la vie du pod.

**US backend-only (justification)** : gestion de connexions dans
`BaseRepository`, aucun contrat, aucun écran.

### Mesure du problème (2026-07-27, banc 200 praticiens via PgBouncer)

Écart entre les backends comptés sur Postgres et ceux que PgBouncer déclare
détenir (`pg_stat_activity` moins `SHOW POOLS`) :

| Tir | `default_pool_size` | Backends pooler | Backends Postgres | **Écart non attribuable** |
|---|---|---|---|---|
| A | 2 | 400 (= 200 bases × 2) | 569 | **~169** |
| B | 1 | 209 (= 200 bases × 1) | 409 | **~200** |

L'écart est **stable autour d'une connexion par base**, indépendamment du
réglage du pooler — signature de la route directe. Il retombe à ~0 quelques
minutes après le tir, ce qui confirme un pool qui expire plutôt qu'une fuite
franche.

### Pourquoi ça n'existait pas avant task-200

Sans pooler, `ConnectionStringUser` (données) et
`ConnectionStringProvisioningUser` (contrôle) sont **la même chaîne** : un seul
pool Npgsql, aucune connexion supplémentaire. Task-200 les a fait diverger
(données → PgBouncer 6432, provisionnement → Postgres 5432 en direct) : deux
chaînes distinctes, donc **deux pools distincts par praticien**. Le surcoût est
donc strictement corrélé au déploiement d'un pooler — c'est-à-dire à
l'architecture cible.

### Deux causes identifiées dans le code

1. **`BaseRepository.CreateServices(...)` retourne un `ServiceProvider`
   (`IDisposable`) qui n'est jamais disposé.** Dans `SetupDatabaseAsync`, seul
   le `scope` interne l'est :
   ```csharp
   var serviceProvider = CreateServices(_userContextInfo!.ConnectionStringProvisioningUser);
   using var scope = serviceProvider.CreateScope();   // le scope, oui ; le provider, non
   UpdateDatabase(scope.ServiceProvider, _userContextInfo!, _logger!);
   ```
   Un conteneur DI FluentMigrator fuit ainsi **par base praticien et par pod**.

2. **La chaîne de provisionnement ne passe pas par `AppendPoolingSettings`.**
   Le chemin de données borne son pool (`Maximum Pool Size`,
   `Connection Idle Lifetime=30`) ; la route directe, elle, part sur les
   **défauts Npgsql** — `Maximum Pool Size=100`, `Connection Idle Lifetime=300`.
   Outre la connexion retenue 5 min, c'est un plafond de 100 connexions par
   base qu'aucune rafale de provisionnement ne borne aujourd'hui.

## Contenu attendu

1. **Disposer le `ServiceProvider` de FluentMigrator** après `UpdateDatabase`,
   y compris sur le chemin d'exception.
2. **Borner explicitement la chaîne de provisionnement.** Elle sert une seule
   fois par base et par pod : `Maximum Pool Size=1`, `Minimum Pool Size=0`, et
   un `Connection Idle Lifetime` court (quelques secondes). À faire via un
   helper dédié plutôt qu'en réutilisant `AppendPoolingSettings`, dont les
   valeurs sont dimensionnées pour le chemin de données.
   ⚠️ **Ne pas transposer aveuglément le raisonnement du chemin de données** :
   l'`Idle Lifetime` y est volontairement **long** (600 s au banc) parce qu'un
   recyclage rapide de ~1 000 pools épuise les ports éphémères Windows
   (200 000 × `SocketException 10048`, mesuré le 2026-07-27, cf. AppHost.cs).
   Ici le volume est tout autre — une connexion par base, une seule fois — donc
   un idle court est sans danger, **mais l'argumenter dans le code**.
3. **Relâcher activement le pool après migration réussie** si le point 2 ne
   suffit pas à ramener l'écart sous le seuil : `NpgsqlConnection.ClearPool` sur
   la chaîne de provisionnement, appelé une fois la base marquée migrée
   (`_migratedDatabases` / cache `setupdb:`).
4. **Ne rien changer hors pooler.** Quand `MSS-MAIL-CONNECTIONSTRING-DIRECT`
   n'est pas défini, les deux chaînes coïncident : le comportement doit rester
   identique à l'octet près, et un test doit le prouver.

## Hors scope

- Le réglage `default_pool_size` de PgBouncer (mesuré au tir B : le passer de
  2 à 1 divise le plancher par deux mais coûte +13 à +32 % de p95 et fait
  apparaître `cl_waiting` — **écarté**, la configuration nominale reste à 2).
- Le plafond de débit de ~900 req/s du banc, identique à 200 et 500 praticiens
  (facteur limitant réel, task séparée).
- Le déploiement PgBouncer en Staging/Prod (équipe système).

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures)
- [ ] Test unitaire : le `ServiceProvider` de FluentMigrator est disposé après
      un provisionnement réussi **et** après un provisionnement en échec
- [ ] Test unitaire : la chaîne de provisionnement porte bien
      `Maximum Pool Size=1` / `Minimum Pool Size=0` / un `Connection Idle
      Lifetime` court, et **n'est pas** modifiée quand l'appelant l'a déjà
      dimensionnée
- [ ] Test d'intégration : hors pooler (variable directe non définie), la
      chaîne de provisionnement est **identique** à la chaîne de données —
      aucun changement de comportement
- [ ] Test d'intégration : après provisionnement d'une base neuve avec PgBouncer
      en place, le nombre de connexions Postgres **directes** attribuables à
      cette base retombe à **0** en moins de 30 s
- [ ] Tir `mixed` 200 praticiens iso-conditions (mêmes paramètres que
      `report-mixed-mssante-60vu-144525.md` : `USERS=200`,
      `MESSAGES_PER_USER=100`, `VUS=60`, `DURATION=5m`,
      **`SESSION_ROTATION=0.001`**) : l'écart
      `pg_stat_activity − SHOW POOLS(sv_total)` sur bases praticien passe de
      **~169 à moins de 20** en régime établi
- [ ] Même tir : **aucune dégradation p95 > 10 %** par opération vs
      `report-mixed-mssante-60vu-144525.md` (le correctif ne doit rien coûter —
      c'est tout son intérêt face à l'option `default_pool_size=1` écartée)
- [ ] Rapport de tir généré (`report.sh --expected 100` + ligne d'INDEX) et
      comparé au tir A dans la task

## Manual Test Plan

1. Monter le banc en profil loadtest (skill `loadtest-skill`) et vérifier que
   `loadtest-pgbouncer` est debout avec `default_pool_size=2` (valeur nominale).
2. Seeder : `dotnet run --project tests/mss.mail.loadtest.seed -- --users 200 --messages 100 --api http://127.0.0.1:5052`
3. Juste après le seed (donc après provisionnement), relever l'écart :
   ```bash
   export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'
   B=$(docker ps --filter "name=loadtest-pgbouncer" --format '{{.Names}}')
   docker exec "$B" env PGPASSWORD=pgbouncer psql -h 127.0.0.1 -p 6432 -U pgbouncer pgbouncer \
     -tAF'|' -c 'SHOW POOLS' | awk -F'|' '$1!="pgbouncer"{sa+=$7; si+=$10} END{print "pooler:", sa+si}'
   docker exec postgres-pgvector psql -U postgres -tAc \
     "select count(*) from pg_stat_activity where datname like 'u\_%'"
   ```
   ⚠️ Ordre réel des colonnes de `SHOW POOLS` : `sv_active` est la **7ᵉ**,
   `sv_idle` la **10ᵉ** — quatre colonnes d'annulation s'intercalent avant.
   **Attendu** : les deux nombres à moins de 20 d'écart (avant correctif : ~169).
4. Tirer : `unset MSYS_NO_PATHCONV MSYS2_ARG_CONV_EXCL` puis
   `BYPASS_KEY=loadtest-local-only USERS=200 MESSAGES_PER_USER=100 SESSION_ROTATION=0.001 tests/loadtest-k6/run.sh mixed --env VUS=60 --env DURATION=5m`
5. Pendant le tir, ré-échantillonner l'écart : il doit rester sous 20.
6. Comparer la table « latence par opération » du rapport à celle du tir A :
   aucune opération ne doit se dégrader de plus de 10 %.
7. Vérifier qu'aucun `NpgsqlException` / `too many clients` n'apparaît dans Seq
   sur la fenêtre du tir.

## Branches

- `api-mail` (pushed) : `fix/task-202-provisioning-connection-release` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-202-provisioning-connection-release
- `dtos-mss` (pushed, auto-inclus) : `fix/task-202-provisioning-connection-release` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/fix/task-202-provisioning-connection-release
  (aucun changement de contrat attendu — branche créée proactivement, pas de PR si aucun commit)

> **Préfixe `fix/`** : la task supprime des connexions retenues pour rien, ce
> n'est pas une nouvelle capacité.

> ⚠️ **Quatre critères de la DOD exigent le banc monté** — les deux tests
> d'intégration « avec PgBouncer en place », le tir `mixed` 200 praticiens
> iso-conditions et son rapport comparé au tir A. Le banc n'est pas debout ; ce
> sont les étapes 1 à 7 du Manual Test Plan, côté humain. Les critères
> réalisables sans banc (dispose du `ServiceProvider`, bornage de la chaîne,
> équivalence hors pooler) sont, eux, du ressort de `/develop`.

## Develop log

- **Repos touchés** : `api-mail` uniquement (C# de production + tests).
  `dtos-mss` : aucun commit, aucun contrat touché → pas de PR.
- **Commit** : `382889f`
  `fix(infra): la route de provisionnement ne retient plus un backend par praticien`
- **Build / tests** : `dotnet build` 0 erreur / 0 avertissement ; `dotnet test`
  **3 219 réussis, 0 échec** (16 ignorés, suite IA `[SKIP]` d'origine) — dont
  **+12** dans `mss.mail.infrastructure.tests` (382 contre 370).
- **Test-first** : les 12 tests ont été écrits avant le code et constatés RED
  (échec de compilation : `BaseRepository` ne contenait ni
  `AppendProvisioningPoolingSettings`, ni `ProvisionDatabase`).
- **Convention S103 vérifiée avant commit** (`awk 'length($0)>150'`) : aucune
  ligne longue introduite.

### Les trois gestes, et ce que chacun corrige

| Geste | Défaut corrigé |
|---|---|
| `using` sur le `ServiceProvider` de FluentMigrator | il n'était **jamais** disposé — un conteneur DI fuyait par base praticien et par pod. Le `using` couvre le chemin d'exception, celui qui compte : une migration en échec est rejouée à la requête suivante |
| `AppendProvisioningPoolingSettings` (`Max=1`, `Min=0`, idle 5 s) | la chaîne partait sur les défauts Npgsql — **100 connexions** par base et un backend retenu **5 minutes** |
| `ReleaseProvisioningPool` (`ClearPool`) après succès | disposer le conteneur rend la connexion au pool, où elle reste oisive ; le vidage la ferme tout de suite. Pas appelé sur échec — rien n'a été provisionné |

Helper **distinct** de `AppendPoolingSettings`, comme l'exigeait l'énoncé : les
deux chemins ont des profils opposés. L'idle du chemin de données est long
**pour une raison** — recycler ~1 000 pools épuise les ports éphémères Windows
(200 000 `SocketException 10048` le 2026-07-27) — et ce raisonnement ne se
transpose pas à une connexion unique par base, jouée une fois. C'est argumenté
dans le code, comme demandé.

### ⚠️ Un piège trouvé en chemin : la chaîne serveur ne doit PAS être bornée à 1

L'énoncé dit « borner explicitement la chaîne de provisionnement ». Il y en a
**deux** :

- la chaîne **utilisateur** (`ConnectionStringProvisioningUser`), unique par
  praticien → c'est elle qui coûtait ~1 backend par base. Bornée à `Max=1` ;
- la chaîne **serveur** (`ConnectionStringProvisioningServer`), utilisée par le
  verrou consultatif et `MigrationHelper` → **unique par pod**, donc pas la
  coupable. Et y poser `Max=1` provoquerait un **interblocage** :
  `lockConnection` reste ouverte pendant que `DatabaseExists` /
  `CreateDatabase` en ouvrent une seconde sur la même chaîne. Il en faut au
  moins deux.

Laissée telle quelle, avec la raison écrite sur place. Si le humain veut tout de
même la borner, `Max=4` serait sûr (2 connexions simultanées au pire, le
provisionnement étant sérialisé par un `SemaphoreSlim(1,1)` statique).

### 📌 Une nuance sur l'énoncé, vérifiée dans le code

La task écrit : « Sans pooler, `ConnectionStringUser` et
`ConnectionStringProvisioningUser` sont la même chaîne : un seul pool Npgsql,
aucune connexion supplémentaire. » Les deux **propriétés** coïncident bien, mais
le chemin de données construit son `NpgsqlDataSource` sur
`AppendPoolingSettings(cs)` — une chaîne **différente**, donc un pool Npgsql
différent. La connexion de provisionnement était donc déjà distincte **avant**
task-200 ; le pooler l'a rendue visible et coûteuse, il ne l'a pas créée. Sans
incidence sur le correctif — mais l'origine du défaut est plus ancienne que ce
que l'énoncé suppose.

### ⚠️ DOD : quatre critères sur huit exigent le banc

Réalisés sans banc :

- [x] Build 0 erreur — tests 0 échec
- [x] `ServiceProvider` disposé après un provisionnement réussi **et** en échec
- [x] Chaîne bornée `Max=1` / `Min=0` / idle court, **et** inchangée quand
      l'appelant l'a déjà dimensionnée
- [x] Hors pooler, la chaîne de provisionnement reste celle du chemin de données
      (test task-200 conservé vert, + un test qui vérifie que le bornage ne
      touche ni l'hôte, ni le port, ni la base)

Non réalisés — **étapes 1 à 7 du Manual Test Plan, côté humain** :

- [ ] Test d'intégration « avec PgBouncer en place » : connexions directes de la
      base neuve à **0** en moins de 30 s
- [ ] Tir `mixed` 200 praticiens iso-conditions : écart
      `pg_stat_activity − SHOW POOLS` de **~169 à moins de 20**
- [ ] Même tir : **aucune dégradation p95 > 10 %** par opération vs le tir A
- [ ] Rapport de tir généré + ligne d'INDEX, comparé au tir A

Le banc n'est pas monté (ni AppHost, ni Dovecot/GreenMail/Toxiproxy/PgBouncer) et
le monter suppose seed de 200 praticiens × 100 messages puis un tir de 5 min.

- **Étape suivante** : `/forge-simplify task-202`.

## Sonar log

- **Phase 1 (new code)** : 1 issue fixée — `csharpsquid:S125`, la seule
  introduite par cette task. **Zéro finding C# restant.**
- **Phase 2 (legacy)** : rien entrepris — les 2 restants sont du Python de
  task-204, sans rapport avec ce diff.
- **Build / tests** : ✓ Release 0 erreur / 0 avertissement ; **3 219 réussis,
  0 échec** (16 ignorés, suite IA `[SKIP]` d'origine).
- **Analyses** : 2 (scan initial → fix → vérification).

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate | ERROR | ERROR | → (2 findings Python de task-204, hors diff) |
| `new_violations` | 3 | **2** | **−1** |
| Bugs | 0 | 0 | = |
| Vulnerabilities | 0 | 0 | = |
| Security hotspots à revoir | 0 | 0 | = (100 % revus) |
| Code smells | 3 | **2** | **−1** |
| Coverage (projet) | 86,6 % | 86,6 % | = |
| New coverage | 86,2 % | 86,2 % | = (seuil 80 % ✓) |
| Reliability / Security / Maintainability | A / A / A | A / A / A | = |

### Le seul finding C#, et pourquoi sa correction est une amélioration réelle

`csharpsquid:S125` « code commenté » sur `BaseRepository.cs`. Faux positif de
forme : l'explication de « pourquoi la chaîne serveur n'est pas bornée » était un
bloc inline dont les puces se terminaient par des points-virgules et citaient des
identifiants — Sonar y a lu du code désactivé. Déplacée dans un `<remarks>` de la
doc XML de `UpdateDatabase`, où elle a de toute façon sa place : c'est une
décision de conception sur la méthode, pas une note sur l'instruction suivante.

### Conventions alimentées

Aucune entrée nouvelle. `conventions/csharp.md` portait déjà `csharpsquid:S103`
(signatures > 150 caractères), dont le contrôle `awk` a été appliqué **avant** le
commit comme la consigne l'exige — aucune ligne longue introduite. `S125` n'a pas
donné lieu à une entrée : il ne s'agit pas d'un pattern à éviter d'emblée mais
d'un artefact de mise en forme d'un commentaire, sans récurrence attendue.

## PRs

- `api-mail` : **https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/134**
  — label `awaiting-human-merge`, `MERGEABLE`, 3 commits, 2 fichiers.
- `dtos-mss` : **aucune PR** — branche sans commit, aucun contrat touché. Ref
  distant supprimé, repo repassé sur `develop`.
- `client-angular`, `client-mobile`, `devops`, `psc-proxy-*` : hors périmètre.

## Code Review Summary

Verdict : **APPROVED** — 0 blocage.

| Fichier | Verdict |
|---|---|
| `src/Infrastructure/Repository/BaseRepository.cs` | ✅ `ProvisionDatabase` isole le contrat de disposition et le rend testable sans base ; les deux helpers de pool partagent leur squelette (`AppendUnlessExplicitlySized`) mais gardent des valeurs distinctes — c'est le propos de la task |
| `tests/.../BaseRepositoryProvisioningPoolTests.cs` | ✅ 12 tests écrits RED d'abord, dont la disposition sur **exception** et le **non**-vidage du pool après échec |

**Validation** : `develop` à 0 commit de retard ; build Release 0 erreur ;
3 219 tests verts ; convention S103 vérifiée avant commit.

## Reste à faire par le humain

1. **Tester puis merger la PR #134** — HAG, règle 10.
2. **Les quatre critères de DOD au banc restent décochés** : test d'intégration
   PgBouncer, tir 200 praticiens iso-conditions, non-régression p95 > 10 %,
   rapport comparé au tir A. Étapes 1 à 7 du Manual Test Plan, recopiées dans le
   body de la PR.
3. À décider si tu le souhaites : borner aussi la chaîne **serveur** de
   provisionnement, à **4 minimum** (jamais 1 — interblocage). Non nécessaire au
   correctif, son pool étant unique par pod.

## Merged

- **Date** : 2026-07-31
- `api-mail` : squash `710cb05` — PR
  [#134](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/134)
  fermée. Ref distant `fix/task-202-provisioning-connection-release` supprimé,
  **branche locale conservée**.
- `dtos-mss` : aucune PR (branche sans commit) — ref distant déjà supprimé au
  `/review`, repo sur `develop`.
- `client-angular`, `client-mobile`, `devops`, `psc-proxy-*` : hors périmètre.
- **Staging** : `forge/staging-task-176-196-20260728` conservée — 202 est hors
  de sa plage `[176, 196]`, et ce run n'est pas drainé.
