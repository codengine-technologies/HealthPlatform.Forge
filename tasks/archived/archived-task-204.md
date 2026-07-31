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

## Acquis du 2026-07-28 — ce que le tir de validité de task-203 a déjà tranché

Ne pas re-découvrir ce qui est mesuré (détail : `## Tir de validité log` de
`tasks/done-task-203.md`) :

- **`k6` n'est pas le goulet** : 0,3 cœur sur 24 pendant un tir saturant. Le mur
  est le **CPU de l'hôte** (93-100 % de 24 cœurs), partagé entre l'infrastructure
  du banc (`vmmemWSL` 9-10 cœurs) et les 5 réplicas (4-6 cœurs).
- **Postgres domine le CPU conteneurs** (188 % en moyenne, 439 % en pointe, soit
  ~60 % du total), **Dovecot est marginal (13 %)** — l'hypothèse « saturé sur
  IMAP » du rapport 500 est écartée. La couche pooler est saine
  (`cl_waiting` ≈ 0, 609 backends).
- **Un tir VALIDE existe** : `RPS=600` (budget 540 req/s) → 0,67 % de drop,
  249/331 VUs, **99,4 % du budget servi**, soit **536,8 req/s sur le plateau**.
- **Le genou est donc entre 540 et 1 080 req/s de budget.** L'escalier doit
  encadrer cet intervalle plutôt que de partir de 600 : paliers **540 → 700 →
  840 → 980 → 1 080** sont plus informatifs que 600/900/1200/1600, et le palier
  1 600 est inutile (l'hôte sature bien avant).
- **Un tir valide au budget nominal est impossible sur cette machine.** À énoncer
  dans le rapport de l'escalier : la capacité mesurée ici est celle d'un banc
  où l'infra de test et l'application se partagent le CPU — donc un **plancher**
  de la capacité réelle, pas son plafond.

**Correction supplémentaire à intégrer** (défaut trouvé pendant le tir) :
`http_reqs.rate` de k6 divise par la fenêtre **totale** du run, arrêt gracieux
inclus (330 s pour un plateau de 300 s). **Tous les débits publiés par le banc
sont sous-estimés de ~8-10 %** — la référence 200 vaut 934,5 req/s et non 915,5,
le tir A 917,0 et non 833,6. `report.py` doit publier un débit calculé **sur le
plateau** (ou nommer explicitement son dénominateur), et l'INDEX doit être
recalculé en conséquence.

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
      **explicite** 540 / 700 / 840 / 980 / 1080, tous **valides** au sens de
      task-203 (`dropped < 1 %`, `vus < vus_max`). Livrer dans la task : la
      courbe « débit demandé → débit délivré », la courbe « débit délivré →
      p95 », le genou, et **la ressource épinglée au genou** — ou la conclusion
      explicite qu'aucune ne l'est jusqu'à 1080 req/s.
      *Paliers réalignés au `/start` du 2026-07-29 sur la section « Acquis du
      2026-07-28 » ci-dessus, qui est postérieure à la rédaction de cette DOD :
      le genou est encadré entre 540 et 1 080 req/s, donc l'escalier doit
      l'encadrer plutôt que de partir de 600, et le palier 1 600 est inutile
      (l'hôte sature bien avant — un tir valide y est impossible sur cette
      machine). L'ancien escalier 600/900/1200/1600 est conservé ici pour
      mémoire.*
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
4. Démarrer l'échantillonneur en **détaché**, puis enchaîner les cinq paliers
   (⚠️ `unset MSYS_NO_PATHCONV MSYS2_ARG_CONV_EXCL` avant `run.sh` ; ⚠️ après
   tout redémarrage d'AppHost, recréer les proxies Toxiproxy par
   `dotnet run --project tests/mss.mail.loadtest.seed -- --users 200 --messages 0`) :
   ```bash
   for R in 540 700 840 980 1080; do
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

## Branches

- `api-mail` (pushed) : `feat/task-204-bench-resource-telemetry` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-204-bench-resource-telemetry
- `dtos-mss` (pushed, auto-inclus) : `feat/task-204-bench-resource-telemetry` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-204-bench-resource-telemetry
- `client-angular` / `client-mobile` : non listés dans `**Repos**:` (`Single frontend: true`) — aucune génération de code frontend

### Pre-flight (2026-07-29)

Tous les repos forge présents sont sur `develop`, arbres propres. Deux écarts
d'environnement, non bloquants et déjà relevés par task-200/task-203 :

- `client-mobile` — `Client/Mobile/` **absent du disque** (repo non cloné).
- `host` — `Host/Modules/` n'est pas un repo git autonome (il appartient au repo
  racine du workspace) ; 6 fichiers modifiés y sont hors périmètre de cette task.

**Dépendance `task-203`** : satisfaite — PR #127 mergée le 2026-07-29 (squash
`0a64cd1`), task archivée en `tasks/archived/archived-task-203.md`. La branche de
cette task part donc d'un `develop` qui porte **l'instrument corrigé** (pools de
VUs par la loi de Little, garde de validité, logs en `Information`).

### Réalignement de DOD au `/start`

L'item « Escalier de capacité » de la DOD portait les paliers
**600 / 900 / 1200 / 1600**, en contradiction avec la section « Acquis du
2026-07-28 » du corps de la task — postérieure — qui établit que le genou est
encadré **entre 540 et 1 080 req/s** et que le palier 1 600 est inutile (l'hôte
sature avant, un tir valide y est impossible sur cette machine). La DOD et le
Manual Test Plan sont réalignés sur **540 / 700 / 840 / 980 / 1080**. L'ancien
escalier est conservé en note dans la DOD.

### Décision humaine encore ouverte — n'empêche pas le code

**Où tirer.** Sur la machine actuelle, l'infra du banc consomme 9-10 cœurs contre
4-6 pour les 5 réplicas : tout chiffre de capacité y est un **plancher**, jamais
un plafond. Deux voies (à trancher avant la session de banc, pas avant le code) :
réduire la contention sur ce poste et publier l'escalier en le **déclarant
plancher**, ou séparer le tireur / l'infra du banc de la machine applicative pour
obtenir un chiffre opposable (arbitrage avec l'exploitant HDS).

Le contenu attendu 1 à 7 (attribution par réplica, échantillonneur, section
« Ressources & télémétrie » de `report.py`, Prometheus par défaut, dashboard de
saturation) **ne dépend pas** de cette décision — `/develop` peut le livrer
intégralement. Seul l'escalier lui-même l'attend.

## Develop log

- **Repos touched** : `api-mail` uniquement. `dtos-mss` : branche créée par
  `/start`, **aucun commit** — aucun contrat touché (US bench/infra), donc aucune
  PR et aucun publish NuGet.
- **DTOs published** : no DTO change. **Interop published** : no interop change.
- **Commits** (`api-mail`, `feat/task-204-bench-resource-telemetry`, poussés) :
  - `7a99e7e` feat(loadtest): attribuer les métriques par réplica via un collector OTLP
  - `358b2d0` feat(loadtest): section « Ressources & télémétrie » et débit au dénominateur nommé
  - `52fa708` feat(loadtest): dashboard de saturation, remote-write par défaut, mode opératoire
  - `f3a724f` fix(loadtest): le fan-out du banc ne doit pas planter les réplicas au démarrage
- **Local build / test** : build **0 erreur / 0 warning** ; suite complète
  **3 194 tests verts, 0 échec**, 16 skips préexistants (tests IA nécessitant des
  clés API). Détail : domain 102, infrastructure 370, **api 589** (+14),
  application 1 852, **integration 281** (+7). Baseline task-203 : 3 173.
- **Auto-tests du harnais** (`tests/loadtest-k6/selftest.sh`, hors `dotnet test`) :
  **11 tests node + 47 tests unittest verts** (35 → 47, +12 sur la nouvelle
  section ; `selftest.sh` passe en `unittest discover` pour qu'un nouveau
  `test_*.py` soit pris en compte sans qu'on pense à le brancher).

### La décision de conception, et l'argument qui a tranché

Le contenu attendu n°1 demandait de choisir entre deux voies « avec un argument
mesuré ». Retenue : **le fan-out OTLP vers un collector**.

| Voie | Ce qu'elle demande | Verdict |
|---|---|---|
| Scrape par réplica (`file_sd`/`http_sd` depuis l'API DCP) | découvrir les **ports dynamiques** des 5 réplicas, et les régénérer à chaque redémarrage du banc | **écartée** — la « méthode déjà éprouvée » citée par la task ne l'est que pour **lire les logs** (`%TEMP%\aspire-dcp*\<guid>_out`), pas pour énumérer des endpoints. Elle plaçait un détail d'implémentation d'Aspire sur le chemin critique de chaque montage de banc. |
| **Fan-out OTLP → collector** | un conteneur et une variable d'environnement | **retenue** — les réplicas **poussent**, donc le problème de découverte **disparaît** au lieu d'être contourné. Le code applicatif était déjà prêt (`AddOtlpExporter`), et le collector promeut `service.instance.id` en étiquette. |

**Fan-out et non substitution**, comme la task l'exigeait : `MSS_BENCH_OTLP_ENDPOINT`
ajoute un **second** exporteur de métriques, celui du dashboard Aspire reste en
place. Un banc ne doit pas aveugler l'outil de diagnostic qu'on regarde pendant
qu'il tourne.

**Pourquoi l'identité est `{machine}-{pid}` par défaut** : l'AppHost ne sait pas
varier une variable d'environnement **par réplica**. Or chaque réplica est un
**processus** — machine + PID les distingue donc par construction, sans rien
demander à l'orchestrateur. `MSS_BENCH_INSTANCE_ID` reste disponible pour forcer
une identité lisible.

### Le défaut que les tests ont attrapé avant le banc, et il était grave

En écrivant un test de coexistence « par acquit de conscience », j'ai trouvé que
**les cinq réplicas auraient planté au démarrage, en profil loadtest et nulle part
ailleurs** :

```
NotSupportedException: Signal-specific AddOtlpExporter methods and the
cross-cutting UseOtlpExporter method being invoked on the same
IServiceCollection is not supported.
```

Sous Aspire, l'AppHost pose `OTEL_EXPORTER_OTLP_ENDPOINT` pour le dashboard, donc
`AddOpenTelemetryExporters` appelle `UseOtlpExporter()`. Or l'API OpenTelemetry
.NET **refuse** de combiner cette méthode transverse avec un `AddOtlpExporter`
par signal. Le fan-out, écrit de la façon la plus naturelle, était donc un crash
au démarrage — et il ne se serait manifesté qu'au **premier montage de banc**,
après le merge, sur la machine de l'humain.

Correctif : le lecteur OTLP du banc est **instancié à la main**
(`PeriodicExportingMetricReader` + `OtlpMetricExporter`), ce qui l'ajoute à ceux
de `UseOtlpExporter` sans passer par le garde-fou du conteneur DI. Le test monte
désormais **les deux endpoints ensemble** et vérifie en plus que la ressource
porte bien l'identité du réplica — sans quoi le collector n'aurait rien à
promouvoir en étiquette et l'attribution serait vide.

### Deux autres corrections trouvées en écrivant les tests

1. **Le débit « plateau » n'a pas de sens pour un `shared-iterations` fini.**
   Le premier recalcul de l'INDEX a sorti `enrich` à **0,4 req/s** pour un tir qui
   en délivrait 1,8 — un chiffre faux dans l'autre sens. Cause : `enrich` s'arrête
   quand sa bande d'UIDs est épuisée, donc sa `duration` n'est qu'un `maxDuration`,
   pas un plateau. Discriminant mécanique retenu : la fenêtre réelle est **plus
   courte** que le plateau annoncé → le rapport écrit « sans objet » au lieu de
   publier un chiffre. Verrouillé par un test.
2. **L'échantillonneur voyait tout Docker.** Le premier run de 30 s a échantillonné
   `sql-server`, `keycloak`, `ollama`, `jaeger`, `mongo`… c'est-à-dire qu'il aurait
   pu désigner **`sql-server` comme « ressource épinglée » d'un tir de charge
   mail**. Exactement la fausse attribution que cette task corrige. Restreint aux
   conteneurs du banc (`loadtest-*`, `mss-mail-*`, `postgres-pgvector`).

### Validation croisée qui donne confiance au calcul de débit

Le débit plateau, recalculé **indépendamment** par `report.py` depuis les JSON
archivés, retombe **exactement** sur les valeurs que task-203 avait calculées à la
main le 2026-07-28 :

| Tir | Publié par k6 | task-203 (à la main) | `report.py` (ce jour) |
|---|---|---|---|
| Référence 200 (2026-07-27) | 915,5 | 934,5 | **934,5** ✅ |
| Tir A (2026-07-27) | 833,6 | 917,0 | **917,0** ✅ |

### DOD self-check

Vérifiés par commande (**8/11**) :

- [x] Build 0 erreur / 0 warning — [x] Tests 0 échec (**3 195**)
- [x] **Métriques attribuables** : `BenchMetricAttributionTests` monte **deux
      instances par le chemin de production** (`ConfigureOpenTelemetry`) et assied
      l'assertion sur l'**étiquette d'instance**, pas sur une valeur — plus le cas
      « aucune identité déclarée » (repli PID) et le cas « hors profil loadtest »
- [x] **`report.py` sur fixtures figées** : `fixtures/prom-telemetry.json`
      (réponses `query_range` réelles, 5 réplicas dont un déséquilibré) +
      `fixtures/observe-sample.csv` → agrégats corrects, 5 réplicas distingués,
      ressource épinglée nommée
- [x] **Prometheus vide / CSV absent → avertissement, jamais de tableau vide** :
      6 tests dédiés (aucune source, fenêtre absente, Prometheus injoignable,
      Prometheus sans point, CSV hors fenêtre, tir archivé)
- [x] **Échantillonneur** : run de 30 s → CSV non vide, **6 instants en UTC**,
      scopes `host` / `process` / `container` / `postgres` (réserve ci-dessous)
- [x] **Hors profil loadtest, aucun changement** — prouvé par test à trois
      niveaux : ressource sans attribut d'instance
      (`OutsideTheLoadTestProfileNoInstanceAttributeIsAdded`), `prometheus.yml`
      inchangé et ignorant le collector, et `MSS_BENCH_OTLP_ENDPOINT` posé
      **sous** le garde-fou `if (loadTestProfile)` de l'AppHost
- [x] **`docs/loadtest.md`** : § 4b (voie d'attribution + son argument + comment
      vérifier qu'elle marche) et § 4c (mode opératoire de l'échantillonneur)

### ⚠️ Ce que ce commit ne prouve pas — à vérifier au premier montage de banc

Le code est en place et testé sur fixtures. **Trois points ne peuvent l'être que
sur un banc réel**, et il faut les regarder dans cet ordre :

1. **Les noms de métriques Prometheus.** `PROM_REPLICA_QUERIES` utilise les noms
   conventionnels d'OpenTelemetry .NET (`process_cpu_time_seconds_total`,
   `dotnet_thread_pool_queue_length`, `http_server_request_duration_seconds_bucket`).
   Ils n'ont **pas** été confrontés à un `/metrics` réel. S'ils ont bougé, la
   section dira « aucun point » — le comportement voulu, pas un plantage — mais
   **l'attribution sera vide**. C'est le premier contrôle à faire :
   `curl http://127.0.0.1:18899/metrics | grep -E 'process_cpu|thread_pool'`.
2. **L'image et la configuration du collector.**
   `otel/opentelemetry-collector-contrib:0.115.1` et la forme du bloc
   `service.telemetry.metrics.readers` ne sont pas validées contre un conteneur
   qui tourne (cette forme a changé entre versions). Contrôle : le conteneur
   `loadtest-otel-collector` démarre et `/targets` montre les deux jobs en `UP`.
3. **Trois sondes de l'échantillonneur.** `doveadm who` (Dovecot), `SHOW POOLS`
   (PgBouncer) et `pg_stat_activity` n'ont pas pu être exercées — les conteneurs
   étaient absents. Elles ont **correctement journalisé leur absence** (12 échecs
   tracés dans `observe-*.csv.log` sur 6 itérations, aucun silencieux), ce qui est
   le comportement voulu, mais leur chemin nominal reste non joué. Idem pour les
   lignes `k6` et les **5 réplicas** : le mécanisme `process` est exercé
   (`vmmemWSL`, `com.docker.backend` sont capturés par la même branche), mais pas
   ces cibles-là.

**Différés au banc / HAG (3/11) — ce sont des tirs, pas du code** :

- [x] **Preuve PromQL de l'attribution** : 5 séries distinctes de `process.cpu` /
      file ThreadPool pendant un tir (contenu attendu n°1) — **fait le 2026-07-29**,
      voir `## Tir de contrôle télémétrie log` ci-dessous
- [ ] **Escalier de capacité** — 200 praticiens, paliers **540 / 700 / 840 / 980 /
      1080**, tous valides au sens de task-203, avec la courbe « demandé →
      délivré », la courbe « délivré → p95 », le genou, et **la ressource épinglée
      au genou**. C'est le livrable qui manque depuis le début de l'EPIC.
- [ ] **Rapport + ligne d'INDEX par palier**, et le facteur limitant **nommé,
      chiffré et sourcé** — chaque finding applicatif ouvrant une task dédiée

### Écarts de procédure, signalés plutôt que passés sous silence

1. **La DOD a été modifiée au `/start`** (paliers de l'escalier réalignés sur
   540 → 1080). `agents/develop.md` interdit à `/develop` de toucher la DOD — c'est
   propriété du PO — et la modification a bien eu lieu **avant** `/develop`, au
   `/start`, pour lever une contradiction interne au fichier. Elle reste **à
   ratifier par le PO** : le motif est écrit dans la task, l'ancien escalier est
   conservé en note.
2. **Test-after sur `BenchTelemetry`** : l'helper a été écrit avant ses tests
   unitaires (la règle est test-first). Les deux tests qui portent le
   **comportement neuf** de la task — l'attribution par réplica et l'absence de
   télémétrie — ont, eux, été écrits contre une implémentation qu'ils ont
   effectivement corrigée (cf. « deux corrections trouvées en écrivant les tests »).
3. **`conventions/csharp.md` lu avant le C#** (CA1822, S2068, CA1861, CA1859).
   CA1861 était applicable et appliqué d'emblée : le tableau d'attributs de
   ressource est hissé en variable locale au lieu d'être un littéral en argument.
4. **Un test a été corrigé par le code, pas l'inverse** :
   `TheLoadTestPrometheusConfigNeverScrapesTheDcpProxy` a échoué parce qu'un
   **commentaire** de `prometheus.loadtest.yml` citait la cible interdite. La
   consigne stricte a été conservée (elle ne peut pas être contournée) et le
   commentaire reformulé.

- Next step : /forge-simplify task-204

## Simplify log

- **Repos passed** : `api-mail` (seul repo touché — 23 fichiers de diff vs
  `develop`).
- **Skipped (contrat / exclus)** : `dtos-mss` (porteur de contrat, et **sans
  diff** — branche créée par `/start`, aucun commit), `interop-cda`, `devops`,
  `psc-proxy-*`.
- **Applied & committed** : `api-mail`, 2 fichiers — `4d28562`
  `refactor(loadtest): passe qualité (/simplify) — task-204` (poussé).

| Axe | Cleanup |
|---|---|
| Réutilisation / altitude | `INSTANCE_LABEL` déclare **une fois** l'étiquette d'attribution, et elle est **interpolée jusque dans les requêtes PromQL**. Le `by (…)` qui produit les séries et l'étiquette qui les relit étaient deux littéraux indépendants (4 occurrences) : les laisser dériver aurait fait retomber les cinq réplicas dans une série indistincte — l'état d'avant la task — **sans qu'aucun test ne le voie**, puisque les fixtures portent l'étiquette en dur. C'est le seul mot dont dépend toute la section. |
| Simplification | `pinned_candidates` : une seule boucle pour les candidats CPU au lieu de deux quasi identiques. Conteneurs et processus produisent le **même** candidat (un CPU en pourcentage d'un cœur, borné par les cœurs de l'hôte) ; seuls les filtres diffèrent, et ils sont désormais des données. |
| Efficacité | `docker ps` relevé **une fois par itération** et non trois (une par sonde `docker exec`). À ~100-300 ms l'appel sur ce poste, c'était ~0,5 s de cadence dépensée à redemander la même liste — sur une boucle dont la cible est 5 s, et qui dérive déjà à cause de `docker stats`. |

- **Écarté** — un helper `table(header, rows)` pour les tables Markdown du
  rapport. task-203 l'avait déjà écarté (n'en refactorer qu'une partie serait
  moins lisible, les reprendre toutes dépasse le diff — règle 6). La task-204 en
  ajoute quatre, donc le dossier se renforce, mais le raisonnement n'a pas changé :
  **candidat à une passe dédiée**, pas à un effet de bord de celle-ci.
- **Écarté** — mémoïser les séries Prometheus dans `build_telemetry` plutôt que de
  rappeler `reduce_prom_matrix` dans chaque rendu. Le gain est nul (les payloads
  d'un tir font quelques Ko) et le coût réel serait de déplacer le choix de
  l'étiquette d'agrégation loin de son usage — soit exactement le couplage que le
  premier cleanup vient de resserrer.
- **Validation** : le rapport régénéré depuis le JSON du tir A est **octet pour
  octet identique** à celui d'avant la passe (diff vide) ; **47 auto-tests du
  harnais verts** ; build 0 erreur ; échantillonneur re-joué 15 s → **mêmes
  cibles, mêmes sondes journalisées** qu'avant la passe. Aucun fichier C# touché
  par cette passe — la suite .NET (3 195 verts) est inchangée. Aucun rollback
  nécessaire.
- **Écart de procédure** : le playbook `/simplify` prévoit 4 agents de revue en
  parallèle. La consigne de session interdit l'Agent tool sans demande explicite
  de l'humain — la revue des 4 axes a donc été faite en direct sur le diff (même
  écart que task-200 et task-203).
- Next step : /sonar task-204 (api-mail touché)

## Sonar log

Mode A (chaîné), **1 itération** sur la branche de la task — aucune seconde n'a été
nécessaire. SonarQube 9.9.8 (`http://127.0.0.1:9000`, conteneurs `sonarqube` +
`sonarqube_db` démarrés par l'agent — ils étaient `Exited`, et **remis dans cet
état** après le scan, l'instance contaminant les mesures du banc), projet
`healthplatform-api-mail`.

| KPI | Baseline (task-203) | **Final (scan 1)** | Cible new-code |
|---|---|---|---|
| Quality Gate | OK | **OK** | OK ✅ |
| Bugs / New bugs | 0 / 0 | **0 / 0** | 0 ✅ |
| Vulnérabilités / New | 0 / 0 | **0 / 0** | 0 ✅ |
| New code smells | 6 | **6** | 0 ⚠️ (voir note) |
| Code smells (projet) | 31 | **31** | — |
| Coverage / New coverage | 86,5 % / 87,7 % | **86,6 % / 87,8 %** | ≥95 ⚠️ (voir note) |
| Maintainability | A | **A** | A ✅ |
| Security hotspots / New | 3 / 0 | **3 / 0** | — |

- **Périmètre task-204 : 0 issue, dès le premier scan.** Aucune correction n'a été
  nécessaire — c'est le résultat qu'on cherche, pas un scan qui n'aurait rien vu :
  les deux fichiers de production de la task sont interrogés nommément et
  ressortent vides.

  | Fichier | Issues | Couverture |
  |---|---|---|
  | `src/Api/Telemetry/BenchTelemetry.cs` (neuf) | **0** | **100 %** (15/15 lignes) |
  | `src/Api/DependencyInjectionExtensions.cs` | **0** | — (classe `[ExcludeFromCodeCoverage]`) |

- **Les 6 new-code smells restantes ne viennent pas de cette task** — ce sont
  **exactement les mêmes six** que task-199, task-200 et task-203 avaient déjà
  imputées à des tasks mergées antérieurement (la période new-code est large) :
  `BackgroundSyncService` S107, `OcspValidationService` S3604 + S1168,
  `MailClientSession` S3604 ×2, `VCardSerializer` S1643. **Aucun de ces fichiers
  n'est touché ici.** Hors périmètre (règle 6) — c'est la quatrième task
  consécutive à les constater, ce qui en fait un candidat mûr pour un
  `/sonar api-mail` standalone (Mode B) plutôt qu'une note de plus.
- **New coverage 87,8 % < 95** : même cause (la période new-code couvre du code
  d'autres tasks). Le code C# de *cette* task est à **100 %**.
- **`conventions/csharp.md` : aucune entrée ajoutée, et c'est le résultat attendu.**
  Le protocole ne consigne que les règles corrigées **à la main** ; zéro correction
  ici. CA1861 était applicable et a été appliqué **d'emblée** (le tableau
  d'attributs de ressource est hissé en variable locale plutôt que passé en
  littéral) — c'est précisément la boucle d'auto-amélioration qui fonctionne :
  la règle apprise en task-203 a évité l'aller-retour en task-204. Aucun compteur
  à incrémenter.
- **Tests** : suite complète verte **en Release avec couverture** — 102 + 1 852 +
  370 + 590 + 281 = **3 195 passés, 0 échec**, 16 skips IA préexistants. Les cinq
  projets sont passés, aucun en échec.

### Deux pièges d'outillage, dont un neuf

1. **Confirmé (task-200, task-203)** : `dotnet sonarscanner` ne reçoit pas ses
   arguments `/k:` `/d:` sous Git Bash. Le scan a donc été lancé par un script
   **PowerShell détaché** — forme qui échappe aussi à la limite de 10 min des
   tâches d'arrière-plan (le scan complet a pris **6 min 22**).
2. **NEUF, et il a coûté un faux départ** : sur ce poste, seul **PowerShell 5.1**
   est installé (`pwsh` absent). Un script `.ps1` contenant des accents et
   enregistré en UTF-8 **sans BOM** est lu en ANSI : le mangling casse le
   *parsing*, et l'erreur qui sort (`CommandNotFoundException` sur un fragment de
   chaîne) ne ressemble en rien à un problème d'encodage. Le premier scan a ainsi
   « réussi » avec un code de sortie 0 **sans rien scanner**. Remèdes :
   **écrire tout `.ps1` accentué avec un BOM UTF-8** (déjà fait pour
   `tests/loadtest-k6/observe.ps1`, qui portait le même risque), et **vérifier le
   parsing avant d'exécuter** :
   ```powershell
   [System.Management.Automation.Language.Parser]::ParseFile($path, [ref]$null, [ref]$null)
   ```

### ⚠️ `SONAR_TOKEN` du `.env` est périmé

Le token stocké dans `.env` (racine du workspace) renvoie **401**. Le scan a été
authentifié avec `SONAR_ADMIN_PASSWORD` du **même fichier**, en `sonar.login` /
`sonar.password` — donc **rien n'a été créé ni modifié** côté SonarQube (aucun
token généré, aucun droit changé). **À la charge de l'humain** : régénérer le
token et remettre à jour `.env`, sinon chaque `/sonar` refera ce contournement.

- Itérations : **1/5** (arrêt immédiat : 0 issue dans le périmètre, KPI au niveau
  de la baseline). Next : /review task-204 (`lint-angular`, `lint-mobile`,
  `verify-visual` : skip — repos non touchés).

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/130
  — label `awaiting-human-merge` (23 fichiers, +3 969/−40)
- `dtos-mss` : aucun changement de contrat — branche sans commit, **pas de PR**
  (build validé : 0 erreur)
- `client-angular` / `client-mobile` : non listés dans `**Repos**:`
  (`Single frontend: true`), non touchés — et `Client/Mobile/` n'est pas cloné
  sur cette machine (cf. Pre-flight)
- Racine du workspace (contrôle plane, hors automation) :
  `questions/task-204.md` **ajouté** (trace du défaut bloquant trouvé en revue),
  `tasks/wip-task-204.md` → `tasks/done-task-204.md`. `conventions/csharp.md`
  **inchangé** — aucune règle corrigée à la main, donc aucune entrée à ajouter.

## Code Review Summary

**APPROVED** — 23 fichiers relus. **2 défauts bloquants trouvés et corrigés**
avant l'ouverture de la PR, 4 suggestions non bloquantes (recopiées dans le body
de la PR).

### Les deux défauts, et pourquoi ils comptent

1. **`f3a724f` — les 5 réplicas auraient planté au démarrage, en profil loadtest
   et nulle part ailleurs.** `AddOtlpExporter` refuse de coexister avec le
   `UseOtlpExporter` qu'Aspire arme via `OTEL_EXPORTER_OTLP_ENDPOINT`
   (`NotSupportedException`). Le fan-out écrit de la façon la plus naturelle était
   donc un crash **au premier montage de banc, après le merge** — le pire endroit
   possible. Trouvé par un test de coexistence écrit par acquit de conscience,
   pas par la relecture.
2. **`ccf711a` — le rapport concluait faux, et avec assurance.** Sans fenêtre de
   tir (29 JSON archivés) et avec un CSV présent, la section agrégeait le fichier
   entier et annonçait « Ressource épinglée : conteneur `postgres-pgvector`
   (CPU) — 87,5 % de sa borne » sur des points hors tir. C'est **exactement** le
   mode d'échec que la task existe pour supprimer, en pire : le chiffre est
   affirmatif et un lecteur le recopie. Traité en **étape de développement**
   (test-first : 3 tests, RED constaté puis GREEN) et non dans `/review`, la revue
   étant en lecture seule sur le code. Détail : `questions/task-204.md`.

### Suggestions non bloquantes

1. `BenchTelemetry.IsEnabled` n'est utilisé que par les tests.
2. `PGPASSWORD=postgres` apparaît **deux fois** dans `observe.ps1` — la convention
   S2068 du workspace dit « une déclaration, N usages ».
3. `report.py` atteint ~1 100 lignes ; le helper de table Markdown écarté par
   task-203 a 4 sites d'appel de plus. Passe dédiée à prévoir.
4. Les **noms de métriques Prometheus** n'ont pas été confrontés à un `/metrics`
   réel — premier contrôle au banc.

### Vérifications conduites pendant la revue, au-delà de la lecture

- **Le cas dégradé a été exécuté, pas raisonné** : c'est en rendant la section
  avec un contexte vide que le second défaut est apparu. Une relecture ne l'aurait
  pas vu — la ligne fautive est un `observe_aggregate(rows, None, None)` d'apparence
  anodine.
- **Le calcul de débit plateau est validé par recoupement externe** : recalculé
  depuis les JSON archivés, il retombe exactement sur les valeurs corrigées à la
  main le 2026-07-28 (référence 200 = 934,5 ; tir A = 917,0).
- **Le correctif du premier défaut est vérifié dans les conditions de son
  échec** : le test monte les **deux** endpoints ensemble (Aspire + banc) et
  vérifie en plus que la ressource porte l'identité du réplica — sans quoi le
  collector n'aurait rien à promouvoir et l'attribution serait vide.
- **Non-régression du cas nominal** après le second correctif : 295 lignes lues,
  59 agrégats, verdict « file ThreadPool du réplica `mss-mail-api-3` » conservé.
- **Périmètre .NET du dernier correctif** : `git diff --name-only 4d28562..HEAD`
  → 2 fichiers `.py` uniquement, donc la suite .NET verte de `4d28562` reste
  valide sans re-run.

### Réserve de méthode

La revue est faite par la forge sur son propre code. Les deux points qui méritent
le plus l'œil humain : le **seuil de 85 %** qui déclare une ressource
« épinglée », et le choix de **borner un CPU de conteneur par les cœurs de
l'hôte** — juste faute de limite `docker` déclarée, mais à revoir si une limite
est posée un jour.

Validation : build 0 erreur / 0 warning (api-mail + dtos-mss) ; **3 195 tests
.NET verts, 0 échec** (16 skips IA préexistants) ; **11 node + 50 python** verts ;
Sonar Quality Gate OK, **0 issue sur le périmètre**, `BenchTelemetry.cs` à
**100 %** de couverture.

**Ce que cette PR ne livre pas** : la mesure. L'escalier de capacité
(540 → 1080 req/s à 200 praticiens), le genou et la ressource épinglée au genou
restent à conduire — c'est un tir, pas du code, et c'est le livrable qui manque
depuis le début de l'EPIC.

## Tir de contrôle télémétrie log — 2026-07-29

**Objet** : lever les **trois points que le commit ne prouvait pas** (§ « ⚠️ Ce que
ce commit ne prouve pas ») **avant** d'engager l'escalier de capacité — tirer cinq
paliers de 3 min sans savoir si l'attribution marche aurait produit cinq rapports
disant « aucun point ». Banc monté une fois, tir `mixed` de 2 min, 20 praticiens
× 10 messages (l'attribution ne demande pas 200 praticiens).

Rapport : `tests/loadtest-k6/reports/2026-07-29/report-mixed-mssante-20vu-193540.md`
(+ `observe-193327.csv`, `seq-*.jsonl`, ligne d'INDEX).
Tir **invalide pour une conclusion de capacité** (1,3 % de drop) — sans importance,
il ne prétend rien mesurer d'autre que la télémétrie.

### Les trois points, tranchés

| # | Point | Verdict |
|---|---|---|
| 1 | **Noms de métriques Prometheus** jamais confrontés à un `/metrics` réel | ⚠️ **3 noms faux sur 13** — corrigés, cf. ci-dessous |
| 2 | **Image + config du collector** (`0.115.1`, forme `service.telemetry.metrics.readers`) | ✅ conteneur `Up`, jobs `mssante-api` **et** `otel-collector` en `UP`, ports 14318/18899/18898 conformes à la doc |
| 3 | **Trois sondes jamais jouées** (`doveadm who`, `SHOW POOLS`, `pg_stat_activity`) | ✅ **les trois répondent** — scopes `dovecot`/`pgbouncer`/`postgres` renseignés, `.csv.log` réduit à son en-tête (zéro sonde en échec), k6 et les 5 réplicas capturés par PID |

**L'attribution fonctionne** (contenu attendu n°1, différé au banc) :
`count(count by (service_instance_id) (process_cpu_time_seconds_total{job="mssante-api"}))`
→ **5**, et la table par réplica du rapport distingue bien cinq CPU/ThreadPool/GC.
Recoupement qui donne confiance : les cinq `service_instance_id`
(`DESKTOP-DEV-X2C-{19024,19720,20268,26408,39192}`) **sont exactement** les PID
`mss.mail.api#…` relevés indépendamment par l'échantillonneur Windows. Les deux
instruments, qui n'ont aucun code en commun, désignent les mêmes processus.

### Les trois noms faux — et pourquoi le banc était le seul moyen de les voir

| Requête | Nom codé | Nom réel | Conséquence observée |
|---|---|---|---|
| File ThreadPool | `dotnet_thread_pool_queue_length` | `…_length_total` | colonne à `—` pour les 5 réplicas |
| Threads | `dotnet_thread_pool_thread_count` | `…_count_total` | colonne à `—` |
| Santé du collector | `otelcol_exporter_send_failed_metric_points_total` | `…_metric_points` (**sans** `_total`) | **le témoin censé interdire une perte silencieuse de métriques était lui-même silencieusement absent** |

Corrigés dans `tests/loadtest-k6/report.py` **et** dans
`src/AppHost/grafana/dashboards/saturation.json`, qui portait les **mêmes** trois
noms — trois panneaux du dashboard de saturation étaient donc vides eux aussi.
Rapport régénéré **sur le même JSON** : `File ThreadPool` = 0-1, `Threads` = 13-17.
Les fixtures sont indexées par `key` et non par la requête PromQL : aucune n'a eu
à bouger, **50 auto-tests du harnais verts**.

Le comportement dégradé a fonctionné comme conçu : nom absent → `—`, jamais une
exception ni un tableau muet. Et le contrôle de non-silence (`prom=` `observe=`
vides) rend bien `⚠️ télémétrie absente — aucune attribution possible` + la marche
à suivre, jamais un tableau vide ni une conclusion.

### Ce que le banc a mesuré au passage — deux réponses, deux findings

**Réponse n°1 — le ThreadPool n'est pas le goulet à cette charge.** File max
**0 à 1** sur les cinq réplicas à 106 req/s. L'hypothèse sync-over-async de
`BaseRepository` ne se manifeste **pas** en famine de ThreadPool ici. À rejouer au
genou (540-1080 req/s) avant d'en conclure quoi que ce soit à charge nominale.

**Réponse n°2 — ressource épinglée : aucune.** La plus sollicitée est un réplica à
**8,5 %** de sa borne ; `cl_waiting` = 0, 76 backends Postgres, Dovecot 0,03 cœur.
Le rapport écrit explicitement « le plafond est ailleurs — chercher du côté des
dépendances sérialisées ». Cohérent avec un tir volontairement modeste.

**Finding A — `SecurityTokenMalformedException` : 12 668 exceptions en 121 s
(105/s, ≈1,2 par requête).** Le banc envoie `X-PSC-Token: loadtest` (non-JWT) et
le code **tente quand même de le parser** malgré `MSS_ENFORCE_PSC_IDENTITY=false`.
Deux conséquences : la mesure de charge n'exerce pas le chemin de production (où le
token est valide), et ce bruit **noie toute exception réelle** dans la colonne
« Exceptions /s » que cette task vient d'ajouter. Les autres familles :
`FolderNotFoundException` 2 758 (le `Sent` absent, connu et bénin),
`HttpRequestException` 28, `IOException` 21. → **task dédiée** (fidélité du banc).

**Finding B — `mssante_imap_session_events_total` n'a aucune série**, alors que
`mssante_imap_sessions_active` en compte 215. Cause lue dans le code :
`MailClientSessionManager.GetOrCreateSession` (ligne 277) insère la session **sans**
appeler `RecordImapSessionEvent`, et c'est ce chemin-là que prend le verrou IMAP —
seul `GetOrCreateImapClientAsync` (ligne 77) enregistre la métrique. Le compteur est
donc **mort dans le pipeline que le banc exerce**, et la ligne « événements de
session IMAP » promise par le contenu attendu n°3 est absente du rapport.
→ **task dédiée** (un site d'insertion non instrumenté).

### Analyse Seq — RAS hors la famille connue

Zéro `Error`/`Fatal` hors `AppendToSentAsync`, **zéro** événement `Debug` (le
niveau `Information` de task-203 tient), **zéro** `Failed to parse entity headers`
(Dovecot sert bien `BODY[part]`), **zéro** 429. Les décomptes de parsing viennent
des compteurs métier (**104 documents / 101 mails** pour 20 lots) et non d'un
`like` sur les logs : l'API SQL de Seq exige une authentification que le banc n'a
pas câblée (`{"Error":"Please log in."}`), et le MCP `seq-local` pagine sans
agréger. Le `.jsonl` est donc un **échantillon déclaré comme tel**, pas un dump
exhaustif.

### État rendu, et deux écarts assumés au protocole de l'étape 6

- AppHost + `dcp.exe` arrêtés, ports 5052/17254/22234/9090/18899 libres,
  conteneurs `loadtest-*` détruits par Aspire. **870 archives CDA en clair**
  purgées de `%TEMP%` (accumulation des campagnes antérieures, pas seulement de ce
  tir). Tables mail des 20 bases `TRUNCATE`, base témoin à 0.
- **Écart 1 — maildir conservé.** `reset-state.sh` supprime le volume
  `loadtest-dovecot-mail` (**3,49 Go**) : c'est le corpus accumulé 200 × 100 de la
  campagne du 2026-07-28. Le supprimer imposerait de re-seeder 20 000 messages
  avant l'escalier. Purge des tables faite **à la main** sur les 20 bases du tir
  pour éviter le pas destructif du script. À revoir si l'escalier doit repartir
  d'un corpus vierge.
- **Écart 2 — 4 conteneurs `mss-mail-*` laissés debout** (`prometheus`, `grafana`,
  `seq`, `redis`) : cycle de vie **Persistent** côté Aspire, et Prometheus retient
  la télémétrie du tir, utile pour recouper l'escalier. Ils seront réutilisés au
  prochain montage.

### ⚠️ Le tir a mesuré un arbre de travail qui bougeait

Pendant le tir, le worktree `api-mail` a reçu du travail **humain en cours** sur
`AppHost.cs`, `otel-collector/config.yaml`, `prometheus.loadtest.yml`,
`observe.ps1` et `BenchObservabilityConfigTests.cs` — un job `bench-observer`
(collector 8890) qui pousse les métriques de l'échantillonneur en OTLP pour que le
dashboard voie l'hôte et les conteneurs. Ces changements **n'étaient pas** dans la
config montée au démarrage du collector (`docker ps` ne publiait pas 8890,
Prometheus ne voyait que 2 jobs). Ce tir décrit donc l'état **d'avant**
`bench-observer` — et deux des panneaux vides qu'il a trouvés
(`pgbouncer_pools_server_active_connections`,
`pgbouncer_pools_client_waiting_connections`, aucune série : aucun exporteur
PgBouncer n'est scrapé) sont précisément ce que ce travail adresse.

**Rien n'a été committé.** Les corrections de noms (`report.py`,
`saturation.json`) sont dans l'arbre de travail, **mêlées** à ce travail humain en
cours — au humain de décider du découpage des commits.

### Ce qui reste dû

- [ ] **Escalier de capacité** — inchangé : 200 praticiens, paliers 540 / 700 /
      840 / 980 / 1080, tous valides au sens de task-203. La porte est maintenant
      ouverte : l'attribution est prouvée et les noms de métriques sont justes.
- [ ] Rapport + ligne d'INDEX par palier, facteur limitant nommé/chiffré/sourcé.
- [ ] Findings A et B : une task chacun.

## Escalier de capacité log — 2026-07-29

**Le livrable qui manquait depuis le début de l'EPIC est là.** Population fixe
200 praticiens, `mixed` 3 min, budget explicite, cinq paliers, chacun avec son
rapport et sa ligne d'INDEX. Et pour la première fois un tir du banc **nomme** son
facteur limitant au lieu de l'inférer.

### Les deux courbes

| Budget demandé | Débit plateau délivré | Servi | Latence moy. | p95 | Abandons | VUs / plafond | Valide | Err. |
|---|---|---|---|---|---|---|---|---|
| **486** req/s (RPS=540) | **482,7** req/s | 99,3 % | 256 ms | 1 111 ms | 0,67 % | 329 / 406 | ✅ | 0,04 % |
| **630** req/s (RPS=700) | **625,4** req/s | 99,3 % | 223 ms | 1 125 ms | 0,74 % | 469 / 553 | ✅ | 0,01 % |
| **756** req/s (RPS=840) | **745,5** req/s | 98,6 % | 290 ms | 1 210 ms | 1,15 % | 581 / 685 | ❌ | 0,03 % |
| **882** req/s (RPS=980) | **824,8** req/s | 93,5 % | 396 ms | 1 309 ms | 4,21 % | 674 / 793 | ❌ | 0,06 % |
| **972** req/s (RPS=1080) | **857,9** req/s | 88,3 % | 591 ms | 1 343 ms | 7,38 % | 822 / 908 | ❌ | 0,26 % |

Rendement marginal du débit : **+99 %**, **+95 %**, puis **+63 %**, **+37 %** du
surcroît demandé.

**Genou : entre 745 et 825 req/s délivrés** (budget 756 à 882). Plafond mesuré :
**~858 req/s**. Les débits sont recalculés **sur le plateau** ; le chiffre publié
par k6 (`http_reqs.rate`) reste sous-estimé de 8-15 % car il divise par la fenêtre
totale, arrêt gracieux inclus.

⚠️ Les débits sont donnés **sur le budget réellement demandé** (90 % de `RPS` :
la part de `enrich` au mix n'est pas un débit imposé), pas sur `RPS` nominal.

### Le facteur limitant, nommé et chiffré : famine de ThreadPool sur `read_list`

| Budget | `read_list` moy | File ThreadPool par réplica | CPU par réplica |
|---|---|---|---|
| 486 req/s | 252 ms | 11 / 7 / 3 / 2 / … | ~0,9-1,4 cœur |
| 630 req/s | 212 ms | 5 / 4 / 4 / 4 / 3 | ~1,0-1,2 cœur |
| 756 req/s | 344 ms | 12 / … | ~1,1 cœur |
| 882 req/s | **714 ms** | **136** / 93 / 13 / 10 / 7 | ~1,1 cœur |
| 972 req/s | **1 533 ms** | **432** / 205 / 68 / 13 / 6 | ~1,2-1,5 cœur |

Deux faits qui ne laissent qu'une lecture :

1. **`read_list` se dégrade d'un facteur ~7** (212 → 1 533 ms) quand les autres
   opérations ne prennent qu'un facteur ~1,5 : `folders` 44 → 167, `search`
   276 → 657, `send` 1 137 → 1 703, `enrich` 2 659 → 4 177 ms.
2. **La file du ThreadPool explose (5 → 432) à CPU quasi constant.** Le réplica le
   plus chargé tient 432 éléments en file avec **1,19 cœur** et 44 threads. Ce
   n'est pas une famine de CPU — c'est du **blocage d'I/O sur des threads du
   pool**, que l'escalade du ThreadPool (1-2 threads/s) ne rattrape pas.

Et la répartition est très inégale entre réplicas (432 / 205 / 68 / 13 / 6), ce
qui exclut une cause globale (base, pooler, IMAP) et pointe un chemin de code.

### L'expérience qui exclut le client — et qui vaut la campagne à elle seule

Objection à lever : ces abandons viennent-ils du harnais ? Testé **deux fois**,
aux deux paliers au-delà du genou. Même budget, même population, **seul** le
plafond de VUs du client change :

| | 882 req/s `tail=8` | 882 req/s `tail=16` | 972 req/s `tail=8` | 972 req/s `tail=16` |
|---|---|---|---|---|
| VUs utilisés | 674 / 793 | 2 144 / 2 182 | 822 / 908 | 2 990 / 3 010 |
| **Débit délivré** | **824,8** req/s | **716,4** (−13 %) | **857,9** req/s | **683,3** (−20 %) |
| Servi | 93,5 % | 81,2 % | 88,3 % | 70,3 % |
| Abandons | 4,21 % | 13,49 % | 7,38 % | **23,92 %** |
| p95 | 1 309 ms | 6 766 ms | 1 343 ms | **14 685 ms** |
| Latence moy. | 396 ms | 2 012 ms | 591 ms | 2 205 ms |
| `read_list` moy | 714 ms | 3 606 ms | 1 533 ms | **5 288 ms** |
| Erreurs HTTP | 0,06 % | 6,41 % | 0,26 % | 3,34 % |
| File ThreadPool | 136/93/13/10/7 | 406/951/579/648/813 | 432/205/68/13/6 | 203/435/484/387/429 |
| CPU par réplica | ~1,1 cœur | 0,8-2,3 | 1,2-1,5 | 0,9-1,6 |

**Plus de concurrence cliente → moins de débit**, aux deux paliers, de façon
monotone, avec un p95 multiplié par 5 puis par 11 et des erreurs HTTP qui
apparaissent — tout cela **à CPU applicatif inchangé**. Le harnais n'était donc
pas la borne : le plafond est **dans l'application**, et le rendement est
**négatif** au-delà du genou. C'est aussi une consigne d'exploitation : ne pas
« pousser » un service déjà au genou, et ne pas dimensionner un client à sa file
d'attente.

Noter au passage que `tail=16` fait déborder les **cinq** réplicas (203 à 484)
alors que `tail=8` n'en chargeait que deux (432 et 205) : la congestion se
généralise, elle ne se déplace pas.

### Ce que la campagne écarte, avec ses chiffres

| Suspect | Mesure au palier le plus haut | Verdict |
|---|---|---|
| CPU applicatif | **3,68 cœurs sur 24** pour les 5 réplicas (15 % de la machine) | écarté |
| CPU de l'hôte | 78-87 % moy, 100 % max — mais **14,93 cœurs pour l'infra du banc** (`vmmemWSL` 7,56 ; Postgres 2,40 ; Docker 1,88 ; `dcp` 1,18) | contamine, ne cause pas |
| PgBouncer | `cl_waiting` ≤ 8 en fenêtre, 2 001 clients multiplexés sur 153-162 serveurs (~13:1) | écarté |
| Dovecot / IMAP | **1 001 sessions, constantes aux 5 paliers** (= 5 × 200 praticiens, exactement le modèle), CPU 0,19 cœur | écarté |
| Postgres | 2,40 cœurs moy, 3,87 max | écarté |
| Client k6 | 0,47 cœur | écarté |

**Corollaire à ne pas perdre** : sur ce poste le banc se dispute la machine avec le
service qu'il mesure (15 % pour l'application, 62 % pour l'infra de test).
**~858 req/s est donc un plancher de la capacité réelle, pas un plafond.**

### Deux campagnes, parce que la première a été jetée — et pourquoi c'est utile

La 1re campagne a sorti **4,6 % d'abandons dès le premier palier**. Diagnostic
avant de relancer, et il a produit deux findings d'outillage :

1. **1 576 des 3 475 abandons étaient structurels** : `mixed_enrich` est un
   `shared-iterations` de `200 × 100 × 0,5 / 5 = 2 000` lots, dont 424 tiennent en
   3 min. k6 compte le reliquat en `dropped_iterations`, ce qui fait **trébucher la
   garde de validité sans qu'aucun VU n'ait manqué**. Contourné par
   `ENRICH_SHARE=0.05` (bande de 200 lots) → **0 abandon `enrich`** aux cinq
   paliers de la 2e campagne. Correction due : task-208.
2. **Le reste était un vrai sous-dimensionnement** de `folders` et `read`, les
   constantes de `vu-sizing.js` (mesurées le 2026-07-27, `read` = 0,16 s) étant
   démenties par la mesure (jusqu'à 1,65 s). Compensé par `VU_TAIL_FACTOR=8`.
   Correction due : task-209 — mais **pas** en élargissant les pools, l'expérience
   ci-dessus montrant que cela aggrave le tir.

### Vérification par base et Seq

`--expected 100` : **~20 000 mails stockés** aux cinq paliers (200 boîtes × 100),
verdict **PASS**, **0 sujet étranger** (assertion de non-mélange), **0
court-circuit d'enrich** (le pipeline CDA a réellement tourné à chaque palier,
grâce à la purge entre paliers). Seq : aucune erreur nouvelle hors les deux
familles connues (`AppendToSentAsync` — pas de dossier `Sent` sur le banc — et le
bruit de `SecurityTokenMalformedException` de task-206).

### Findings ouverts en tasks

| Task | Finding | Portée |
|---|---|---|
| **205** | `read_list` bloque des threads du pool et plafonne l'API à ~858 req/s | **application — le facteur limitant** |
| **206** | Une `SecurityTokenMalformedException` par requête (>1 200/s au plus haut palier) | fidélité du banc + observabilité |
| **207** | `mssante_imap_session_events_total` mort dans le chemin exercé | télémétrie |
| **208** | Le rapport conclut faux de 3 façons (`cl_waiting` sur un transitoire, dénominateur de la fenêtre totale, garde de validité vs scénario fini) | outillage — conclusions |
| **209** | Le dimensionnement des VUs suppose des latences que le banc ne produit plus | outillage — dimensionnement |

### DOD de task-204 — les 3 items différés au banc

- [x] **Preuve PromQL de l'attribution** — 5 séries distinctes, recoupées avec les
      PID de l'échantillonneur (§ « Tir de contrôle télémétrie log »).
- [x] **Escalier de capacité** — les deux courbes, le genou (745-825 req/s
      délivrés), et **la ressource épinglée au genou nommée** : la file du
      ThreadPool des réplicas. Réserve honnête : **deux des cinq paliers sont
      valides** au sens strict de task-203 (486 et 630 req/s) ; les trois autres
      portent 1,2 à 7,4 % d'abandons, et la campagne **démontre** (expérience de
      discrimination) que ces abandons sont l'**effet** du facteur limitant
      applicatif, pas un défaut du harnais. La conclusion de capacité tient ; la
      case « tous valides » de la DOD, non.
- [x] **Rapport + ligne d'INDEX par palier** (6 lignes, dont l'expérience de
      discrimination), et **facteur limitant nommé, chiffré et sourcé**, chaque
      finding ouvrant sa task.

## Merged — 2026-07-31

| Repo | PR | Squash commit | Branche distante |
|---|---|---|---|
| `api-mail` | [#130](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/130) — closed | `c10fa7b0822929426fcb9cd99f41caa2b211f757` (2026-07-31T10:11:48+02:00) | supprimée (locale conservée) |
| `dtos-mss` | aucune (branche sans commit) | — | supprimée (locale conservée) |
| `client-angular` / `client-mobile` | non listés dans `**Repos**:` | — | — |

- **CI `develop` (api-mail)** : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/30615454945
- **Staging** : `forge/staging-task-176-196-20260728` **conservée** — sa plage
  `[176, 196]` ne contient pas 204, et 21 tasks de ce run sont encore en `todo-*`.

### Un tour de `/merge` a été refusé, et il a rattrapé une perte de preuve

Le premier `/merge 204 --i-tested` a **avorté sur la garde 6** (arbre de travail
sale) : `tests/loadtest-k6/reports/INDEX.md` portait **8 lignes non committées**
— celles de l'escalier de capacité du 2026-07-29, que la DOD réclame
(« chaque palier a son rapport et sa ligne d'INDEX ») et que le
`## Escalier de capacité log` cochait déjà.

L'enjeu n'était pas cosmétique : les rapports eux-mêmes sont **gitignorés par
conception** (`.gitignore:386` — `tests/loadtest-k6/reports/*`, seule exception
`!…/INDEX.md`), donc ces 8 lignes sont la **seule trace versionnée** de la
campagne qui a nommé le facteur limitant de l'EPIC — et le point de départ de
l'avant/après que task-205 doit publier. Merger en l'état les aurait laissées
dans un worktree local.

Committées par l'humain (`f783e58` « Update index »), CI re-passée verte
(build 1 m 28 s), merge relancé. **Vérifié sur `develop` après merge : les 8
lignes y sont** (`grep -c "60vu-20" INDEX.md` → 8). Trace :
`questions/merge-task-204.md`.
