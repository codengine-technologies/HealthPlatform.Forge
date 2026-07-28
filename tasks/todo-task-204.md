# todo-task-204.md — Le banc doit mesurer les ressources et la télémétrie de l'application, pas les inférer

**Repos**: api-mail
**Dependencies**: task-203 (un tir non valide ne peut rien attribuer)
**Epic**: E015
**Single frontend**: true

> **Origine** : la campagne du 2026-07-27 a conclu « saturé sur IMAP + CPU »
> (`report-mixed-mssante-150vu-141351.md` §« Finding ») **sans qu'aucune
> ressource n'ait été échantillonnée pendant le tir** — ni CPU hôte par
> processus, ni CPU par conteneur, ni compteur runtime .NET. C'était une
> inférence. Aucun tir du banc n'a jamais pu **nommer** son facteur limitant.

## Objective

Faire du banc un instrument qui **attribue** la saturation : à la fin d'un tir,
le rapport doit dire *quelle ressource est épinglée* (CPU d'un réplica, CPU du
client k6, CPU de Dovecot/Postgres, file du ThreadPool, connexions DB…) et non
pas seulement à quel débit le tir a plafonné.

Deux moitiés complémentaires :
- **la télémétrie applicative existe déjà et n'est pas exploitable** — la rendre
  exploitable puis l'analyser dans le rapport ;
- **ce que la télémétrie ne voit pas** (le client k6, les conteneurs, l'hôte) —
  l'échantillonner.

**US backend/bench-only (justification)** : profil loadtest de l'AppHost,
outillage du banc et `report.py` — aucun contrat, aucun écran.

### Ce qui existe déjà (et qu'il ne faut pas réécrire)

L'application est **déjà bien instrumentée** — `ConfigureOpenTelemetry`
(`src/Api/DependencyInjectionExtensions.cs`) enregistre :

- `AddAspNetCoreInstrumentation()` → `http.server.request.duration` (**la latence
  vue du serveur**, à confronter à celle vue de k6) ;
- `AddRuntimeInstrumentation()` → **file du ThreadPool**, nombre de threads, GC,
  contention — exactement les compteurs qui trancheraient l'hypothèse
  sync-over-async de `BaseRepository` ;
- `AddProcessInstrumentation()` → **CPU et mémoire du processus** ;
- `AddHttpClientInstrumentation()`, `AddSqlClientInstrumentation()` (traces) ;
- le meter métier `Mssante.MailProcessing` (mails traités, durée du pipeline IA,
  événements de session IMAP, sync, recherche, **durée de traitement CDA**…) ;
- un exporteur **Prometheus** (`MapPrometheusScrapingEndpoint`, `Program.cs:217`).

Et le banc a déjà **Prometheus** (scrape 5 s) + **Grafana** (dashboards
`k6-loadtest.json`, `mssante-mail-processing.json`), et `run.sh PROM=1` sait
pousser les métriques k6 dans le même Prometheus (`--web.enable-remote-write-receiver`
est actif). **Rien de tout cela n'est lu par le rapport de tir.**

### Le point dur : les métriques ne sont pas attribuables par réplica

`AppHost.cs` déclare `.WithReplicas(5)` avec un endpoint HTTP **à port fixe**
(`WithHttpEndpoint(port: 5052, name: "metrics")`), et `prometheus.yml` scrape une
cible unique :

```yaml
static_configs:
  - targets: ["host.docker.internal:5052"]
```

Ce port est le **proxy DCP** devant les 5 réplicas : chaque scrape tombe sur un
réplica **au hasard**. Conséquences, à énoncer dans la task avant de coder :

- les compteurs (`*_total`) reculent d'un scrape à l'autre → `rate()` produit du
  bruit, voire des trous ;
- les gauges runtime (file ThreadPool, threads, CPU process) décrivent **un
  réplica différent à chaque point** — inutilisables pour dire « un réplica est
  saturé » ;
- `/metrics` partage la surface HTTP de l'API : le scrape traverse le même
  pipeline que la charge.

Deux voies, à **trancher avec un argument mesuré** (c'est le cœur de la task) :

1. **Push OTLP par réplica vers un OpenTelemetry Collector** (conteneur du profil
   loadtest) qui expose `/metrics` avec l'étiquette d'instance et/ou fait du
   remote-write vers le Prometheus du banc. Le code applicatif est **déjà prêt** :
   `AddOpenTelemetryExporters` bascule sur `UseOtlpExporter()` dès que
   `OTEL_EXPORTER_OTLP_ENDPOINT` est défini. ⚠️ ne pas priver le dashboard Aspire
   de sa télémétrie (fan-out, pas substitution).
2. **Scrape par réplica** via un `file_sd`/`http_sd` généré au démarrage du banc
   depuis l'API DCP (les endpoints réels des 5 réplicas y sont listés — méthode
   d'interrogation déjà éprouvée, cf. `questions/` et la mémoire de banc).

### Ce que la télémétrie ne verra jamais

Le processus **k6** lui-même (le banc doit pouvoir prouver que le client n'est
pas le goulet), les conteneurs (Dovecot, Postgres, PgBouncer, Redis, RabbitMQ,
Seq — tous sur la même machine que les 5 réplicas et que k6), et l'hôte Windows
(CPU total, file processeur). D'où l'échantillonneur.

## Contenu attendu

1. **Attribution par réplica** : mettre en œuvre la voie retenue (1 ou 2), et
   **prouver** l'attribution — une requête PromQL doit distinguer les 5 réplicas
   et montrer 5 séries de `process.cpu` / file ThreadPool distinctes pendant un
   tir. Documenter le verdict et le pourquoi (ADR courte ou section de
   `docs/loadtest.md`).
2. **Échantillonneur hôte + conteneurs** (`tests/loadtest-k6/observe.sh` ou
   `tools/bench-observe/`) : un **CSV unique**, horodaté **UTC**, cadence 5 s
   alignée sur le scrape Prometheus, colonnes au minimum —
   - CPU total hôte + longueur de la file processeur Windows ;
   - CPU/mémoire du processus **k6** et de **chaque** réplica `mss.mail.api`
     (par PID) ;
   - `docker stats` (CPU %, mém, I/O réseau) pour chaque conteneur du banc ;
   - connexions IMAP actives de Dovecot, `SHOW POOLS` agrégé de PgBouncer
     (⚠️ `sv_active` est la **7ᵉ** colonne, `sv_idle` la **10ᵉ**),
     `pg_stat_activity` sur bases praticien.
   Lancé et arrêté **en processus détaché** (`Start-Process … -WindowStyle Hidden`) :
   un tir + rapport dépasse les 10 min des tâches d'arrière-plan de l'outil.
3. **Section « Ressources & télémétrie » dans `report.py`** : interroger
   Prometheus (`http://127.0.0.1:9090/api/v1/query_range`, stdlib `urllib`,
   aucune dépendance nouvelle) sur la fenêtre du tir + replier le CSV de
   l'échantillonneur, et produire :
   - un tableau **par réplica** : CPU moyen/max, file ThreadPool max, threads,
     pauses GC, exceptions ;
   - un tableau **par conteneur** et pour **k6** : CPU moyen/max ;
   - **p95 client (k6) vs p95 serveur (`http.server.request.duration`)** par
     opération — *le juge* : un écart large signe une file **hors** application
     (client, proxy DCP, réseau), un écart nul signe une saturation interne ;
   - les compteurs métier `Mssante.MailProcessing` de la fenêtre (mails traités,
     durée CDA, événements de session IMAP) ;
   - une ligne **« ressource épinglée »** : la ressource la plus proche de sa
     borne au débit maximal atteint, ou explicitement **« aucune — le plafond est
     ailleurs »**.
4. **Ne jamais conclure en silence** : si Prometheus n'a pas de point sur la
   fenêtre, ou si l'échantillonneur n'a pas tourné, la section doit l'**écrire**
   (`⚠️ télémétrie absente — aucune attribution possible`) au lieu de sortir un
   tableau vide. C'est le mode d'échec récurrent de ce banc (cf. `report.sh` qui
   annonçait trois fichiers sans en écrire aucun).
5. **Prometheus par défaut au banc** : `run.sh`/`run.ps1` activent la sortie
   `experimental-prometheus-rw` pour les tirs de campagne (aujourd'hui derrière
   `PROM=1`), afin que métriques client et serveur soient dans le même TSDB et
   comparables par une seule requête.
6. **Dashboard Grafana « saturation »** : une rangée à côté de l'existant —
   CPU par réplica, CPU k6, CPU par conteneur, file ThreadPool, backends
   Postgres, `cl_waiting` — pour suivre l'escalier **en direct** au lieu de
   l'autopsier.
7. **Hors profil loadtest, aucun changement** : pas de collector, pas
   d'échantillonneur, pas de bascule d'exporteur.

## Hors scope

- Corriger le facteur limitant que la campagne révélera (sync-over-async
  `BaseRepository.get_DataContext`, sémaphore statique global de
  `UpdateDatabase`, plafond IMAP Dovecot, coût des logs…) : **une task par
  finding**, une fois nommé et mesuré.
- Le plancher de connexions par base sous PgBouncer (structurel, déjà documenté)
  et task-202.
- Le déploiement du collector en Staging/Prod (équipe système).

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures)
- [ ] Test d'intégration : les métriques d'un réplica sont **attribuables** —
      2 instances lancées, chacune produit ses propres séries identifiées
      (l'assertion porte sur l'étiquette d'instance, pas sur une valeur)
- [ ] Test unitaire `report.py` : à partir d'un jeu de réponses Prometheus et
      d'un CSV d'échantillonnage **figés en fixtures**, la section « Ressources &
      télémétrie » est produite avec les bons agrégats
- [ ] Test unitaire `report.py` : Prometheus vide / CSV absent → la section
      affiche l'avertissement d'absence, **jamais** un tableau vide ni une
      conclusion
- [ ] Échantillonneur : un run de 30 s produit un CSV non vide couvrant hôte,
      k6, les 5 réplicas et tous les conteneurs du banc, en UTC
- [ ] Hors profil loadtest, aucun changement de comportement (prouvé par test)
- [ ] `docs/loadtest.md` : la voie d'attribution retenue est documentée avec son
      argument, et le mode opératoire de l'échantillonneur est écrit
- [ ] **Escalier de capacité — le livrable qui manque depuis le début** :
      à population **fixe** 200 praticiens, tirs `mixed` de 3 min à `RPS`
      **explicite** 600 / 900 / 1200 / 1600 (1600 = 8 req/s par identité, sous
      le rate-limiter de task-090), tous **valides** au sens de task-203
      (`dropped < 1 %`, `vus < vus_max`). Livrer dans la task : la courbe
      « débit demandé → débit délivré », la courbe « débit délivré → p95 », le
      genou, et **la ressource épinglée au genou** — ou la conclusion explicite
      qu'aucune ne l'est jusqu'à 1600 req/s
- [ ] Chaque palier a son rapport (`report.sh`) et sa ligne d'INDEX
- [ ] Le facteur limitant (ou son absence) est **nommé, chiffré et sourcé** dans
      la task ; chaque finding applicatif ouvre une task dédiée

## Manual Test Plan

1. Monter le banc en profil loadtest (skill `loadtest-skill`), avec les logs en
   `Information` (task-203).
2. Vérifier l'attribution : `http://127.0.0.1:9090/targets` (ou l'API du
   collector) montre **5** instances api-mail distinctes ; dans Grafana, la
   rangée « saturation » affiche 5 courbes de CPU, pas une.
3. Seeder 200 × 100 :
   `dotnet run --project tests/mss.mail.loadtest.seed -- --users 200 --messages 100 --api http://127.0.0.1:5052`
4. Démarrer l'échantillonneur en **détaché**, puis enchaîner les quatre paliers
   (⚠️ `unset MSYS_NO_PATHCONV MSYS2_ARG_CONV_EXCL` avant `run.sh`) :
   ```bash
   for R in 600 900 1200 1600; do
     BYPASS_KEY=loadtest-local-only USERS=200 MESSAGES_PER_USER=100 \
     SESSION_ROTATION=0.001 RPS=$R \
       tests/loadtest-k6/run.sh mixed --env VUS=60 --env DURATION=3m
   done
   ```
5. Pendant les paliers, ouvrir Grafana (`http://localhost:3001`) et regarder
   **où** ça monte : CPU des réplicas, CPU de k6, CPU de Dovecot, file du
   ThreadPool, `cl_waiting`.
6. Générer les quatre rapports (`report.sh --expected 100`) et lire la section
   « Ressources & télémétrie » : elle doit désigner une ressource épinglée au
   palier où le débit délivré décroche du débit demandé.
7. Contrôle de non-silence : couper Prometheus, régénérer un rapport → la section
   doit afficher l'avertissement d'absence de télémétrie.
8. Vérifier dans Seq qu'aucune erreur nouvelle n'apparaît du fait de
   l'instrumentation (le collector ne doit pas devenir une source d'échecs).
