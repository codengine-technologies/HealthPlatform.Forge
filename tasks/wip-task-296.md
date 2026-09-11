# todo-task-296.md — Le Postgres du banc est à sa limite mémoire : un login prend 10 à 16 s et tout le palier 1000 en découle — redimensionner le conteneur et le prouver par un A/B

**Repos**: devops
**Dependencies**: todo-task-295 (instrumentation du coût de login — la lecture « avant/après » se fait sur ses séries ; à défaut, le `psql` chronométré à la main reste opposable)
**Epic**: E015
**Single frontend**: true
**Priorité**: **1** — c'est la **cause racine mesurée** des quatre tirs du 2026-09-09 :
refus `08P01` du pooler, drain d'audit qui ne suit pas, lectures disque, et donc toute
latence médecin à 1000 non opposable. `DevOps/` est hors automation : cette US est un
**acte humain au banc** (skill `loadtest-skill`), pas une US de code — la forge n'y écrit
rien, `/start` ne crée aucune branche.

> **Origine** : campagne task-292 du 2026-09-09 (`Docs/audits/api-mail-loadtest-journey-1000-task292-*.md`,
> findings **F-292-2** et **F-292-6**) et `Docs/plan_remediation_fable.md` § 4 (phase 2). Le
> conteneur `postgres-pgvector` (`DevOps/Dev/PostgreSQL/docker-compose.yml`) tourne avec
> `limits.memory: 12G`, `shared_buffers=4GB`, `effective_cache_size=8GB`, `max_connections=2500`,
> pour **54 Go** de bases praticien hydratées.

## Objective

Que, à 1000 médecins en régime, **l'ouverture d'un backend Postgres redevienne une opération
courte** (sous la seconde), pour que le pooler cesse de rejeter, que le journal d'audit draine au
rythme où il émet, et que les 11 étapes du parcours médecin soient lues sans délestage.

### Ce qui a été mesuré (2026-09-09, quatre tirs journey 1000, mêmes bases)

| Grandeur | Valeur | Source |
|---|---|---|
| Usage mémoire du cgroup / limite | **11,99 / 12 Go**, dont 9,58 Go de cache de pages, 4,14 Go `shared_buffers`, 1,3 Go RSS | `memory.usage_in_bytes`, `memory.stat` |
| Échecs d'allocation à la limite (`memory.failcnt`) | **+15 600 par seconde** en régime | relevé à 20h00 |
| Login d'un backend (`psql -h 127.0.0.1 -d u_9… -c 'select 1'` dans le conteneur) | **10 à 16 s** ; référence saine 6 ms | six mesures à 20h00 |
| Backends créés par seconde | **~3,8** (113 `backend_start` récents en 30 s) | `pg_stat_activity` |
| Backends en attente de lecture disque | 27 (`IO/DataFileRead`) | `pg_stat_activity` |
| Conséquences | refus PgBouncer `08P01` 646 (drain série) → 15 873 (drain parallèle) ; drain d'audit 0,2-0,45 trace/s par réplica pour ~4/s émises ; HTTP 500 724 → 14 280 | rapports task-292 |
| Hôte | 64 Go de RAM, **37 Go libres** pendant le tir | `free -m` |

**Mécanique établie.** Le cache de pages est compté dans le cgroup : avec 54 Go de données pour
12 Go de limite, il remplit tout l'espace et chaque nouvelle lecture oblige le noyau à récupérer
de la mémoire avant de servir. Un `fork` de backend (login) et une lecture de page paient ce
travail ; à 12 cœurs de charge le login passe de 6 ms à 15 s. `max_connections` n'est jamais
atteint (aucun `53300`) : ce n'est pas un plafond de connexions, c'est un plafond de mémoire.

### Contenu attendu

1. **Redimensionner le conteneur** (`DevOps/Dev/PostgreSQL/docker-compose.yml`) : `limits.memory`
   12G → **24G** (jambe A) ; `effective_cache_size` 8GB → 16GB ; `shared_buffers` inchangé à 4GB
   (≤ 25 % de la RAM conteneur) ; `max_connections` **inchangé** à 2500 (le monter masquerait le
   problème). Si la jambe A ne ramène pas le login sous 1 s : 32G + `shared_buffers=8GB` (jambe B).
   Rappel : les flags `-c` ne s'appliquent qu'à `docker compose up -d --force-recreate` ; contrôler
   `show shared_buffers` / `show effective_cache_size` après recréation.
2. **Mesurer par A/B, à conditions égales**, sur les 1000 bases **gardées** (ne pas purger : l'âge
   de la base fait partie des conditions) : protocole journey 1000 r2 (`1000:12600s`, réserves
   365..462 / 463..536 / 537..611, traitement 0,095, froid 0,19, corpus fileté 0,3,
   `UID_BASE=365`, cluster 192.168.1.69, latence `101 − RTT`), code `develop` figé sur le même SHA
   pour les deux jambes, journal d'audit **actif**. Référence de la jambe « 12 Go » : le tir de
   confirmation task-292 du 2026-09-10 (`report-journey-1000-task292-fix2-20260909-010943.md`).
3. **Lire trois grandeurs, sur la même grille de temps** (task-295 si livrée, sinon relevés manuels
   toutes les 5 min en régime) : coût du login (p95, s), débit de création de backends (/min),
   `memory.failcnt` (/s). Et les effets : refus `08P01`, `cl_waiting`, `mss_audit_backlog_lag_seconds`,
   `IO/DataFileRead`, erreurs k6, 11 étapes SLO.
4. **Mettre à jour la source de vérité** : `DevOps/DIMENSIONNEMENT-POSTGRESQL-API-MAIL.md` (formule
   « RAM conteneur ≥ shared_buffers + backends × 5 Mo + marge » à compléter par le **jeu de travail
   des bases hydratées**, absent aujourd'hui), tableau des paliers, et le rappel dans le skill
   `loadtest-skill` (« Le palier 200 exige une configuration précise »).
5. **Ne pas** toucher à PgBouncer dans cette US (task-294 : `server_login_retry`, `server_idle_timeout`,
   `max_db_connections`) — un seul facteur par jambe, sinon l'A/B ne prouve rien.

### Hors périmètre (explicite)

- Le réglage PgBouncer (task-294) et l'instrumentation du login (task-295).
- Le Postgres de Staging/Production (`DevOps/Staging/PostgreSQL/postgresql.yaml`, 1 Gi) : cette US
  dimensionne le **banc** ; le portage vers les environnements HDS est une décision DevOps séparée,
  éclairée par la formule mise à jour.
- Le coût applicatif de la page d'en-têtes hydratée (E015, task-273) : la mémoire n'y change rien
  sur le fond, elle ne fait que rendre le palier lisible.

## Definition of Done

- [x] `DevOps/Dev/PostgreSQL/docker-compose.yml` : `limits.memory` ≥ 24G, `effective_cache_size`
      cohérent (≥ 16GB), `shared_buffers` ≤ 25 % de la limite, `max_connections` inchangé ;
      commentaire daté citant cette US et la mesure d'origine
- [x] Contrôle post-recréation consigné : `show shared_buffers`, `show effective_cache_size`,
      `docker inspect --format '{{.HostConfig.Memory}}'`
- [ ] Deux tirs journey 1000 iso (12 Go de référence = tir task-292 `fix2` ; jambe A ≥ 24 Go), même
      SHA de code, mêmes bases non purgées, rapports dans `Docs/audits/`
- [~] Mesure consignée dans cette US (jambe A faite, critère de sortie NON atteint → jambe B) : login p95 (référence 10-16 s), backends créés/min,
      `failcnt`/s, refus `08P01`, `cl_waiting`, retard du journal d'audit, erreurs k6, 11 étapes SLO
      — **critère de sortie** : login p95 < 1 s en régime, `failcnt` ÷ 10, `08P01` = 0 avec
      `server_login_retry` inchangé, cgroup < 85 %
- [ ] Si la jambe A échoue au critère : jambe B (32G, `shared_buffers=8GB`) jouée et consignée, ou
      `questions/task-296.md` ouverte avec les mesures
- [ ] `DevOps/DIMENSIONNEMENT-POSTGRESQL-API-MAIL.md` mis à jour (formule avec jeu de travail,
      tableau des paliers, section Dev), et le skill `loadtest-skill` (prérequis du palier 200/1000)
- [ ] Aucune donnée de santé réelle : banc `loadtest-*` uniquement

## Manual Test Plan

- **Pré-vol** (skill `loadtest-skill`, mode distant) : bases gardées (`select count(*) from "Mails"`
  non nul sur une base témoin), `docker logs` PgBouncer sans `server_login_retry`, files bus à 0,
  garde scratch `%TEMP%\mss-ihe-xdm` et keep-awake armés avec preuve.
- **Jambe référence (12 Go)** : déjà jouée — `Docs/audits/api-mail-loadtest-journey-1000-task292-fix2-20260910.md`.
  Ne la rejouer que si le code `develop` a bougé depuis.
- **Jambe A** : éditer le compose (24G / 16GB), `docker compose up -d --force-recreate postgres-pgvector`,
  contrôler les `show …`, puis `cd Api/Mail && MSS_LOADTEST=true MSS_ENFORCE_PSC_IDENTITY=false
  MSS_LOADTEST_MAIL_HOST=192.168.1.69 aspire run --project src/AppHost`, seed `--messages 0`, tir
  journey 1000 r2 (`USERS=1000 MESSAGES_PER_USER=247 UID_BASE=365 CORPUS_THREAD_SHARE=0.3
  JOURNEY_P_TREATMENT=0.095 JOURNEY_P_READ_COLD=0.19 JOURNEY_STAGES=1000:12600s LATENCY_MS=<101−RTT>`).
- **Pendant le régime (dernières 38 min)**, toutes les 5 min : login chronométré
  (`docker exec postgres-pgvector psql -U postgres -h 127.0.0.1 -d <u_9…> -c 'select 1'`),
  `memory.failcnt` (+/10 s), `select count(*) from pg_stat_activity where backend_start > now()-interval '60 s'`.
- **Ce que l'humain doit voir** : login < 1 s, `failcnt` quasi plat, 0 refus `08P01` dans les logs
  PgBouncer, `mss_audit_spill_pending` qui reste bas ou redescend en régime, `docker stats` Postgres
  sous 85 % de sa nouvelle limite, rapport `report.sh` + analyse Seq.
- **Contre-épreuve** si tout est vert : remettre 12G, rejouer 30 min de régime, revoir le login monter — sinon la RAM n'était pas la cause.
- **Données de test** : boîtes `loadtest-*`, `JEUX_TESTS_FULL`. Aucune donnée de santé réelle.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors exigence DSR directe — dimensionnement d'infrastructure du banc
- **Exigences DSR honorées** : non applicable — capacité, pas fonctionnalité
- **INS** : non applicable — aucune donnée patient réelle ; bases synthétiques `loadtest-*`
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : indirect — le journal d'audit (task-292) dépend de la capacité de login
  Postgres pour drainer ; cette US est ce qui lui permet de suivre l'émission à 1000
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non — banc de charge local ; le portage des valeurs vers Staging/Production
  HDS est une décision DevOps séparée
- **AIPD / impact RGPD** : inchangée — aucun traitement nouveau

## Forge log

- **`/start` refusé par conception, et ce n'est pas un échec** — `**Repos**: devops`. `DevOps/` est **entièrement hors automation** (CLAUDE.md § « Excluded repos ») : la forge n'y crée aucune branche, n'y écrit aucun code, n'y lance ni build ni test, et n'ouvre aucune PR. La task elle-même le déclare (« acte humain au banc, pas une US de code »).
- **Statut** : `managed manually by the human`. La task reste en `todo-*` — elle attend l'humain, pas la forge.
- **Ce que la forge a pu préparer, et qui est livré** : task-295 (PR api-mail #228) arme les trois sondes dont cette US a besoin pour lire son A/B « avant / après » sur une même série temporelle — coût d'un login (référence saine 6 ms, 10-16 s pendant l'incident), débit de création de backends, pression mémoire du cgroup. La dépendance déclarée est donc **satisfaite côté outillage**, sous réserve du merge humain de la PR #228 (HAG, règle 10).
- **Ce qui reste à l'humain** (cf. `## Manual Test Plan`) : éditer `DevOps/Dev/PostgreSQL/docker-compose.yml` (jambe A : `limits.memory` 24G, `effective_cache_size` 16GB), recréer le conteneur, contrôler les `show …`, puis conduire les deux tirs journey 1000 iso sur bases gardées et consigner la mesure. Environ 3 h 30 par tir sur le banc distant.
- Run `/forge` : `forge-20260911-295-297` — task sautée, passage à la suivante.

## Timings

*(généré par `tools/timing/report.sh --task task-296 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | skipped | 23 s | — | — | — | devops only — no branch, manual bench act |
| **Total cycle** | | **23 s** | **0 (0.0 s)** | **0 (0.0 s)** | **0 (0.0 s)** | |

## Branches
> **Mode** : task `devops` uniquement — repo **hors automation** (CLAUDE.md « Excluded repos »). Aucune branche créée, `/develop` n'écrit rien : l'implémentation est un **acte humain au banc** (édition de `DevOps/Dev/PostgreSQL/docker-compose.yml` + recréation du conteneur), puis mesure A/B par le skill `loadtest-skill`. `/start` du 2026-09-11, après merge de task-295 (`5855604`, préalable déclaré).
- `devops` (manual) : managed manually by the human — `DevOps/Dev/PostgreSQL/docker-compose.yml`

### Jambe de référence « 12 Go » — proposition
Le tir post-lot `journey-1000-postlot-292-294-20260911` (`Docs/audits/api-mail-loadtest-journey-1000-postlot-292-294-20260911.md`, develop `d04f2ca`, 12 Go, ROUGE) est plus proche du code de la jambe 24 Go que le `fix2` du 09/09 désigné par la DOD : task-295 (mergée depuis) ne touche que le harnais, le système sous test est identique. Écarts à consigner : RTT 6 ms (latence injectée 95 → 101 ms simulés), Postgres redémarré le matin du tir. Mesures de référence relevées : backends créés/60 s 344 → 0 à 10h50, `sv_login` max 467, `memory.usage` 11,6-11,7 / 12 Go, `failcnt` 159 M, 110 693 refus `08P01`, erreurs k6 11,98 %.

## Jambe A — recréation du conteneur (2026-09-11, ~13h40)

Édition de `DevOps/Dev/PostgreSQL/docker-compose.yml` (repo `devops`, **non commitée** — branche locale `feature/setup_k8s`, git à la main de l'humain) :
`limits.memory` 12G → **24G**, `effective_cache_size` 8GB → **16GB**, `shared_buffers` 4GB et `max_connections` 2500 inchangés, commentaire daté citant cette US et les mesures des 09/09 et 11/09.
`docker compose config` validé, puis `docker compose up -d --force-recreate`.

| Contrôle | Attendu | Relevé |
|---|---|---|
| `show shared_buffers` | 4GB | **4GB** |
| `show effective_cache_size` | 16GB | **16GB** |
| `show max_connections` | 2500 | **2500** |
| `docker inspect … HostConfig.Memory` | 25769803776 | **25769803776** |
| `memory.limit_in_bytes` (cgroup) | 25769803776 | **25769803776** |
| `memory.usage_in_bytes` / `failcnt` au démarrage | — | 297 Mo / **0** |
| Bases `u_9%` | 1000 | **1000** (volume `pgdata` conservé, bases hydratées gardées) |

Prêt pour la jambe A : journey 1000 iso (bases gardées, journal actif, `develop` = `5855604` avec task-295), référence 12 Go = tir post-lot du 2026-09-11.

## Jambe A — tir lancé (2026-09-11 14h28, `journey-1000-task296-legA-24G-20260911`)

- **Système sous test** : `d04f2ca` (= SHA du tir de référence 12 Go du matin) via un worktree détaché `Api/Mail-ref` — **pas** le tip de `develop` (`5855604`), parce que `cf685ac` (« Migration to Xunit.V3 + update package », 11h52) change ~40 paquets de production (Npgsql EF, EF Core, OpenTelemetry, Aspire, MessagePack 2→3, Dtos 458→467, Host.Sdk 12→13) : un second facteur, interdit par le point 5 de cette US. Le harnais (k6, `observe.ps1` avec task-295, `report.py`) tourne depuis `Api/Mail` sur `develop`.
- **Un seul facteur** : Postgres 12G → 24G, `effective_cache_size` 16GB. Bases gardées (1000, 57 Go), journal actif, RTT 5 ms → `LATENCY_MS=96`, même plan journey (`1000:12600s`, réserves 365/463/537, traitement 0,095, froid 0,19, corpus 0,3).
- **Instrumentation task-295 active** (relevés à +5 min) : login 7 ms, backends créés/60 s 27, cgroup 43 % (7,0 Go), `majfault/s` 0, `sv_login` 0, `cl_waiting` 0.
- **Incidents de pré-vol, corrigés avant le tir** (aucun effet sur la mesure, à consigner dans le skill) :
  1. Le rattachement automatique de PgBouncer au réseau `postgresql_default` (task-257) n'a pas eu lieu après la recréation du conteneur Postgres (« DNS lookup failed: postgres-pgvector ») → `docker network connect` manuel. Le contrôle `getent ahosts postgres-pgvector` du pré-vol reste obligatoire.
  2. Lancer l'AppHost depuis un autre chemin (worktree) crée une seconde famille de conteneurs persistants (`-ab5b4678`) qui partagent les **mêmes volumes nommés** que la première (`prometheus-data`, données Seq) : Prometheus/Seq neufs sortent en « lock DB directory » tant que ceux du matin tournent. Arrêt des `-b6152948`, démarrage des `-ab5b4678` ; historique Prometheus du matin conservé (même volume). Les ~12 premières minutes de séries k6/serveur côté Prometheus sont perdues (rampe), pas le résumé k6 ni Seq.

## Jambe A — résultat (2026-09-11, 14h28 → 17h58) — 🔴 ROUGE, 24 Go insuffisants, jambe B requise

Rapport : `Docs/audits/api-mail-loadtest-journey-1000-task296-legA-24G-20260911.md` (copie de
`Api/Mail/tests/loadtest-k6/reports/2026-09-11/report-journey-1000-task296-legA-24G-20260911-175909.md`). Référence 12 Go :
`Docs/audits/api-mail-loadtest-journey-1000-postlot-292-294-20260911.md` (même jour, même SHA `d04f2ca`, mêmes bases).

| Grandeur (critère de sortie de la DOD) | Cible | 12 Go (matin) | **24 Go (jambe A)** |
|---|---|---|---|
| Login p95 en régime | < 1 s | 10-16 s (manuel 09/09) | **1,0 s sur le tir, 160-300 s en régime** ❌ |
| `memory.failcnt` (cumul) | ÷ 10 | 159 M | **50,2 M** (÷3,2) ❌ |
| Refus `08P01` (`server_login_retry` inchangé) | 0 | 110 693 | **2 099** (÷53) ❌ |
| cgroup | < 85 % | 100 % | **100 % dès +52 min** ❌ |
| Erreurs k6 tir / régime | — | 11,98 % / 28 % | **0,37 % / 1,5 %** |
| Backends créés/min (max) · `sv_login` max | — | 344 · 467 | 740 · 157 |
| Fautes de page majeures (cumul · max/s) | — | 9,2 M | 3,87 M · 1 120/s |
| Journal d'audit | 0 perte | 0 perte | **0 perte** (191 459 = 191 459) |

Lecture : la spirale (`sv_login` → `server_connect_timeout` → `server_login_retry` en cache → `08P01`) est **la même**, déclenchée
**2 h 20 plus tard** (17h10 au lieu de 10h55) et **30 à 50 fois moins violente**. Le cgroup sature à 15h20 ; le cache recule de 20,5 à
14,6 Go pendant que les backends montent de 900 à 2 100 (`server_idle_timeout=600` × 1000 pools × `max_db_connections=3`) ; les fautes
majeures partent quand le cache passe sous ~18 Go (16h00), le login dépasse 1 s à 16h40, 300 s à 17h10. Le jeu de travail utile de
1000 bases hydratées (57 Go, un catalogue système par base) ne tient pas dans 24 Go.

Décision : **jambe B** (32 Go + `shared_buffers` 8 Go, point 1 de l'US), même protocole, même SHA `d04f2ca`. Attendu : recul
supplémentaire de la spirale, pas forcément sa disparition — mesurer la pente. À instruire hors task (un facteur par jambe) :
plafond de backends résidents (`server_idle_timeout` 600 → 60-120 ou `max_db_connections` 3 → 2), cache d'échec de login PgBouncer,
plafond de connexions du rejeu d'audit (post-tir : 2 500 backends, 29 000 « too many clients », 6 min d'administration refusée —
la vérification par base du rapport a dû être rejouée à la main : 1000 bases, 123 949 mails, 0 mélange, PASS).

## Jambe B — 48 Go (décision humaine du 2026-09-11 18h : « beaucoup de marge sur cette machine, passer directement à 48 Go et mesurer ce dont Postgres a réellement besoin »)

- `DevOps/Dev/PostgreSQL/docker-compose.yml` (non commité côté `devops`, à la main de l'humain) : `limits.memory` 24G → **48G**, `shared_buffers` 4GB → **12GB** (25 %), `effective_cache_size` 16GB → **36GB**, `max_connections` 2500 inchangé. Recréé à 18h20 ; contrôle : `show shared_buffers` 12GB, `show effective_cache_size` 36GB, `HostConfig.Memory` 51539607552, cgroup 49 152 Mo, `failcnt` 0, 1000 bases intactes.
- Budget : hôte **191 Go** de RAM (129 libres), VM Docker Desktop plafonnée à **62,8 GiB** ; 48G + ~10 Go des autres conteneurs (sqlserver 2,6, sonarqube 2,7, seq 1,2, keycloak 1,0…) ≈ 58 Go : tient, sans marge pour monter plus haut sans relever la VM.
- **Tir lancé 18h31** : `journey-1000-task296-legB-48G-20260911`, SUT `d04f2ca` (worktree `Api/Mail-ref` recréé), harnais `develop`, bases gardées, journal actif, RTT 5,2 ms → `LATENCY_MS=96`, même plan. Pré-vol entièrement vert (attache PgBouncer automatique cette fois, Prometheus prêt, 200 au premier poll, remote-write k6 sans erreur). Fin prévue ~22h02.
