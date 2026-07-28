# todo-task-202.md — Libérer les connexions de la route de provisionnement : ~1 backend Postgres retenu par praticien, pour rien

**Repos**: api-mail
**Dependencies**: task-200 (mergée — c'est elle qui a introduit la route directe)
**Epic**: E015
**Single frontend**: true

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
