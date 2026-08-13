# todo-task-257.md — Le garde-fou de l'upstream PgBouncer teste le nom, pas la famille d'adresses : il a laissé passer la panne qu'il devait empêcher

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune. Le correctif a été **éprouvé au banc** pendant
task-255 puis **retiré de sa branche** (arbitrage du 2026-08-13,
`questions/task-255.md`) : il faisait tomber le garde-fou existant et n'est pas
complet sans son pendant `AppHost.cs`. Il est reproduit **intégralement en
annexe** de cette US, qui le livre entier et protégé par un test.
**Priorité**: **1** — **le banc de charge est cassé aujourd'hui**, et de la façon
la plus coûteuse qui soit : **silencieusement**. Il ne lève pas d'erreur, il perd
13 % des lots et dégrade le chiffre mesuré. Deux campagnes complètes ont déjà été
jetées pour cette cause ; toute mesure prise avant ce correctif est à écarter.

## Objective

Que le banc parle à PostgreSQL par une route **déterministe et IPv4**, sans
intervention manuelle, et qu'un test échoue si quelqu'un rétablit une route
dépendante de la résolution de `host-gateway`.

## Ce qui est établi — la panne, mesurée le 2026-08-13 (task-255)

`--add-host=pgupstream:host-gateway` injecte aujourd'hui **deux** entrées dans
le `/etc/hosts` du conteneur PgBouncer :

```
192.168.65.254        pgupstream
fdc4:f303:9324::254   pgupstream
```

PgBouncer retient l'**AAAA**, échoue en `sbuf_connect failed … Network
unreachable`, **met l'échec en cache** pour `server_login_retry`, et pendant ce
temps **tout** client du pool reçoit `PostgresException 08P01: server login has
been failing, cached error` — en **8 ms**, ce qui ressemble à un rejet applicatif
et non à une panne d'infrastructure.

| Constat | Mesure |
|---|---|
| Lots d'enrichissement perdus, premier tir | **13 %** |
| Après retrait de l'entrée IPv6 de `/etc/hosts` | **2,6 %** — le contournement **ne marche pas** |
| Après bascule sur le réseau du conteneur PostgreSQL | **0 %** sur 6 tirs et 3 840 messages |

**Deux campagnes complètes ont été jetées** avant que la cause soit établie.

**Pourquoi le garde-fou existant n'a rien vu.** task-200 avait déjà rencontré
cette panne sur `host.docker.internal` et posé le test
`BenchUpstream_DoesNotRelyOnHostDockerInternal`. Ce test vérifie **le nom
utilisé**. Or le nom n'a pas changé — c'est **ce en quoi il résout** qui a
changé, parce que Docker Desktop a ajouté un enregistrement AAAA à
`host-gateway`. Le test protégeait la lettre du correctif, pas sa raison d'être.

**C'est la troisième occurrence de la même cause racine sur ce banc** (relais
IPv6 loopback de Docker Desktop, `host.docker.internal` en AAAA seul, et
maintenant `host-gateway` en A+AAAA). Le point commun n'est pas Docker : c'est
qu'**un client qui ne bascule pas d'une famille d'adresses à l'autre transforme
ce piège en panne totale**, là où `psql` ou `curl` le traversent sans le voir.

## Ce que la US doit livrer

1. **Le rattachement réseau, dans `AppHost.cs`** — le conteneur PgBouncer doit
   être membre du réseau du conteneur PostgreSQL du banc et l'adresser par son
   nom, sans qu'aucun `docker network connect` manuel ne soit nécessaire. C'est
   ce que fait déjà le fichier `pgbouncer.ini` de task-255 ; il lui manque son
   pendant côté orchestration.
2. **Un garde-fou qui teste la bonne chose** : que l'upstream effectivement
   utilisé **résout en IPv4 et en IPv4 seulement**, et qu'aucune route du banc
   ne dépend de `host-gateway` ni de `host.docker.internal`. Un test sur le nom
   ne suffit pas — c'est précisément ce qui a échoué.
3. **Un contrôle pré-vol** utilisable par le skill : une commande qui répond
   « 0 » quand la route est saine, et qui **nomme** le problème sinon.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que figer l'IPv4 littérale suffit.** `192.168.65.254` est
  une valeur de Docker Desktop ; sur un autre hôte la passerelle diffère. C'est
  un contournement portable seulement en apparence.
- **Ne pas présumer que le problème est PgBouncer.** Il ne fait pas de bascule
  d'adresse, ce qui est un choix défendable ; le défaut est dans la route qu'on
  lui donne.
- **Ne pas élargir au dimensionnement du pooler.** `default_pool_size`,
  `max_db_connections` et compagnie sont hors périmètre : task-255 les a mesurés
  calmes (`cl_waiting` nul sur 14 relevés sur 15, `maxwait` maximal 0,7 ms).
- **Ne pas toucher au chemin de contrôle.** Le provisionnement (verrou
  consultatif, `CREATE DATABASE`, `MigrateUp`) parle à PostgreSQL **en direct**
  et doit continuer.

## Definition of Done

- [ ] Build passe (0 erreur), tests passent (0 échec)
- [ ] Un démarrage du banc **sans aucune commande manuelle** rend un PgBouncer
      qui sert : `SHOW POOLS` répond **et** une requête applicative aboutit
- [ ] `docker logs` du conteneur PgBouncer ne contient **aucune** occurrence de
      `Network unreachable` ni de `server_login_retry` après un démarrage propre
      suivi d'un tir court
- [ ] Un **test automatisé** échoue si l'upstream du banc redevient dépendant de
      `host-gateway` / `host.docker.internal`, **ou** s'il résout en autre chose
      qu'une IPv4 — le test porte sur la **famille d'adresses résolue**, pas sur
      la chaîne de caractères
- [ ] Le test porte un commentaire qui **nomme les trois occurrences** de la
      cause racine, pour que la prochaine ne reparte pas de zéro
- [ ] Le skill `loadtest-skill` documente le contrôle pré-vol en une commande
- [ ] Hors profil `loadtest`, **rien ne change** : aucun conteneur PgBouncer,
      aucune variable, comportement identique à aujourd'hui

## Manual Test Plan

- `cd Api/Mail && dotnet run --project src/AppHost --launch-profile https-load-test`
  — **sans** exécuter le moindre `docker network connect`
- Attendre que `http://127.0.0.1:5052/api/v1/connection/status` réponde 200
- Seeder 4 praticiens × 20 messages, puis lancer `tests/loadtest-k6/run.sh enrich --env VUS=4`
- **Ce qu'il faut voir** : 0 % d'erreur HTTP, et
  `docker logs <pgbouncer> | grep -cE 'unreachable|server_login_retry'` = **0**
- Contre-épreuve du garde-fou : remettre `host=pgupstream` dans `pgbouncer.ini`
  et vérifier que le test **échoue**
- Vérifier qu'un `docker exec <pgbouncer> getent ahosts <upstream>` ne rend
  **que** des adresses IPv4

Données de test synthétiques uniquement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — outillage de banc
- **Exigences DSR honorées** : aucune — aucun changement fonctionnel
- **INS** : sans objet — aucune donnée de santé ne transite par ce changement,
  qui ne concerne que le profil `loadtest` et des données synthétiques
- **Interop CI-SIS** : sans objet
- **Habilitations** : ⚠️ le cloisonnement « une base par praticien » ne doit pas
  être affaibli — la route change, **pas** l'isolation : chaque base garde son
  pool et aucune connexion n'est partagée entre praticiens
- **Authentification PS / Consentement** : inchangés
- **Tracé PGSSI-S** : inchangé
- **Hébergement HDS** : sans objet — le profil `loadtest` est interdit hors poste
  de développement, et le hard-block sur `ASPNETCORE_ENVIRONMENT=Production`
  reste en place
- **AIPD / impact RGPD** : inchangé

## Annexe — le correctif, déjà éprouvé au banc, à reprendre tel quel

Ce correctif a tourné pendant la campagne task-255 et a rendu **0 occurrence sur
6 tirs et 3 840 messages**. Il a été **retiré de la branche de task-255**
(arbitrage humain du 2026-08-13, `questions/task-255.md`) parce qu'il fait tomber
le garde-fou existant et qu'il n'est pas complet sans son pendant `AppHost.cs` :
il appartient donc **entièrement** à cette US.

### 1. `src/AppHost/pgbouncer/pgbouncer.ini`

Remplacer la ligne d'upstream :

```ini
- * = host=pgupstream port=5432 user=postgres password=postgres
+ * = host=postgres-pgvector port=5432 user=postgres password=postgres
```

et remplacer le commentaire qui la précède (celui qui affirme que `pgupstream`
« resout en IPv4 de facon deterministe » — c'est cette affirmation qui est
devenue fausse) par le constat de task-255 : deux entrées injectées, A **et**
AAAA, PgBouncer retient l'AAAA, l'échec est mis en cache, tous les clients du
pool prennent un `08P01`.

### 2. `src/AppHost.cs` — ce qui manque

Rattacher le conteneur PgBouncer au réseau du conteneur PostgreSQL du banc, pour
que `postgres-pgvector` soit résoluble sans geste manuel. Aujourd'hui l'équivalent
se fait à la main :

```bash
docker network connect postgresql_default $(docker ps --filter name=loadtest-pgbouncer --format '{{.Names}}')
```

⚠️ **Sans ce point 2, le point 1 seul casse le banc au démarrage** — l'upstream
ne résout pas du tout. Les deux vont ensemble, c'est la raison d'être de cette US.

### 3. `BenchUpstream_DoesNotRelyOnHostDockerInternal` — l'assertion à réécrire

`tests/mss.mail.integration.tests/Repository/PgBouncerTransactionPoolingTests.cs:284`

```csharp
Assert.DoesNotContain("host.docker.internal", upstream);   // à garder
Assert.Contains("pgupstream", upstream);                   // ❌ le mauvais invariant
```

La seconde assertion teste **le nom**. C'est elle qui a laissé passer la panne :
le nom n'avait pas changé, seule sa résolution avait changé. Le nouvel invariant
doit porter sur **la famille d'adresses effectivement résolue** et sur
**l'absence de dépendance à un alias d'hôte** (`host-gateway`,
`host.docker.internal`). Un test qui se contente de remplacer `pgupstream` par
`postgres-pgvector` reproduirait le défaut à l'identique.

### Vérification de non-régression, mesurée

```bash
docker logs --since 5m <conteneur-pgbouncer> 2>&1 | grep -icE 'unreachable|server_login_retry'
```

Doit valoir **0** après un démarrage propre suivi d'un tir court. Valait 13 % de
lots perdus avant correctif, 2,6 % avec le contournement par `/etc/hosts` (qui ne
marche pas), 0 % avec la bascule réseau.
