# todo-task-298.md — À 1000 médecins, les connexions Postgres croissent avec le temps jusqu'à `max_connections` : borner le drain du journal d'audit et découpler les backends résidents de la durée du tir

**Repos**: api-mail
**Dependencies**: — (task-296 jambe B mesurée le 2026-09-11 ; la mémoire du Postgres de banc est réglée à 48 Go)
**Epic**: E015
**Single frontend**: true
**Priorité**: **1** — c'est le **facteur limitant suivant** du palier 1000, désigné par la
mesure : la mémoire réglée (task-296), le tir reste ROUGE parce que Postgres est **plein**
(2 504 backends = `max_connections` 2 500) après 2 h 46, indépendamment de la charge.
Tant que ce plafond tient, aucun verdict SLO à 1000 n'est opposable. Deux réglages, un
facteur par jambe.

> **Origine** : jambe B de task-296, 2026-09-11 18h31 → 22h02
> (`Docs/audits/api-mail-loadtest-journey-1000-task296-legB-48G-20260911.md`), code
> `develop` `d04f2ca`, Postgres 48 Go, 1000 bases hydratées, journal d'audit actif.
> Cause **mesurée** sur la grille task-295 (backends, `started_last_60s`, `cl_waiting`,
> `maxwait`) et attribuée par Seq (`SourceContext` des exceptions `53300`).

## Objective

Que le nombre de backends Postgres à 1000 médecins soit **borné et indépendant de la durée**
du service — gouverné par la population et par l'activité, jamais par « depuis combien de
temps le serveur tourne » — de sorte que `max_connections` ne soit **jamais** atteint en
régime, ni par le pooler, ni par la route directe du journal d'audit.

### Ce qui a été mesuré (jambe B, 48 Go, login p95 80 ms — la mémoire n'est plus en cause)

| Grandeur | Valeur | Lecture |
|---|---|---|
| Backends Postgres | **270 à 18h40 → 2 504 à 21h17** (+2 h 46), linéaire | croissance ∝ **temps** : le débit k6 plafonne à ~130 req/s dès 20h40 et les backends continuent de monter |
| Backends venant du pooler (max) | **2 499** | 1000 pools × `max_db_connections = 3`, serveurs gardés **600 s** (`server_idle_timeout`, task-294) → borne théorique 3 000 > 2 500 |
| Backends directs (sonde `observe.ps1`, max) | 0 relevé | ⚠️ **non fiable** : la sonde classe par réseau `172.x` ; la route directe arrive par la passerelle Docker `172.x.0.1` et est comptée « pooler » — à corriger dans cette US (voir DOD) |
| Postgres « `53300` sorry, too many clients already » pendant le tir | **118 886** (≈1 700/min de 21h17 à 22h02) | refus de **tout** nouveau backend, pooler et direct |
| … côté api-mail (Seq, 53 456 exceptions) | `AuditBackgroundService` **52 088 (97 %)**, `AuditTraceRepository` 1 029, `MailRepository` 126, `UserSettingsRepository` 87, `GlobalExceptionHandler` **67** | le plafond frappe d'abord le **drain du journal**, le médecin n'en voit que la queue (67 × 503) |
| PgBouncer | `cl_waiting` non nul sur **28 %** des relevés, `maxwait` **12,3 s**, 175 refus `server_login_retry` | le pooler attend (task-294), puis rejette quand un login serveur tombe en timeout faute de backend |
| Erreurs k6 | **0,024 %** (290 / 1 233 799), p95 4,8 s | tir « presque » vert — c'est ce plafond qui fait le reste |
| Après le tir | rejeu du spill : backends **2 500** en 3 min, 27 575 refus, administration Postgres refusée, **VM Docker figée 45 min** | le drain ouvre ~1 connexion directe par base rejouée ; 3e occurrence de la journée |

**Mécanique établie.** Deux termes s'additionnent :

1. **Pooler** : `default_pool_size = 2`, `reserve_pool_size = 1`, `max_db_connections = 3`,
   `server_idle_timeout = 600` (porté de 60 à 600 par task-294 pour supprimer le churn de
   login qui coûtait 10-16 s sous pression mémoire — pression **levée** par task-296). À
   1000 bases, tout pool touché dans les 10 dernières minutes garde ses 2-3 serveurs : les
   backends s'accumulent jusqu'à la borne 3 000, au-delà de `max_connections`.
2. **Route directe du journal d'audit** (task-292) : `Maximum Pool Size = 2` **par base**
   (`BaseRepository.AuditMaxPoolSize`), `Connection Idle Lifetime = 60`, drain série
   (`DrainParallelism = 1`) mais **sans plafond global** : un rejeu de spill qui parcourt les
   1000 bases ouvre jusqu'à 1000-2000 connexions directes en quelques minutes, en concurrence
   frontale avec le pooler. C'est ce qui sature Postgres **après** chaque tir et pendant la
   spirale.

### Contenu attendu — deux jambes, un facteur chacune, dans cet ordre

**Jambe 1 — borner le drain d'audit (code api-mail, profil de banc inchangé).**
- Un **plafond global** de connexions directes ouvertes simultanément par le drain (toutes
  bases confondues), configurable (`Audit:DrainMaxConnections`, défaut proposé **16**),
  réalisé par une limite de concurrence côté drain (les pools Npgsql par base restent à 2 ;
  c'est le nombre de bases drainées **en même temps** qui est borné) — le rejeu du spill
  devient une opération **lente et sûre**, jamais une tempête.
- **Fermeture des connexions directes après drain** : `Connection Idle Lifetime` du chemin
  d'audit ramené à **≤ 30 s** et `Connection Pruning Interval` ≤ 10 s ; après un rejeu, les
  backends directs redescendent à 0 en moins d'une minute (mesurable : `pg_stat_activity`
  filtré par `application_name`).
- **`application_name` explicite** sur la route directe (`mss-mail-audit`) et sur la route
  de provisionnement (`mss-mail-provision`), pour que la sonde et Postgres puissent
  **attribuer** les backends sans deviner par l'adresse IP (c'est ce qui a rendu la colonne
  « directs » fausse le 11/09).
- Invariants task-292 conservés : 0 perte, contre-pression au lieu de perte, aucune donnée de
  santé en clair dans le nouveau chemin, interrupteur de banc inchangé.

**Jambe 2 — découpler les backends du pooler de la durée (profil de banc `pgbouncer.ini`).**
- `server_idle_timeout` 600 → **120** (compromis : recyclage 5× plus lent qu'au réglage
  d'origine, mais un pool inactif rend ses serveurs en 2 min au lieu de 10) **ou**
  `max_db_connections` 3 → **2** (borne 2 000 < 2 500). **Une seule** des deux par tir ;
  la première est préférée (ne réduit pas la capacité d'un pool actif).
- `server_login_retry` et `query_wait_timeout` (task-294) **inchangés**.
- Le portage vers `DevOps/` reste un acte humain, hors forge.

**Ce que ce n'est pas** : ni un relèvement de `max_connections` (masquerait le problème et
recréerait la pression mémoire mesurée par task-296 : ~2,5 Mo de RSS par backend), ni un
retour de `server_idle_timeout` à 60 (churn de login mesuré le 09/09), ni une optimisation
des requêtes du médecin (backlog E015 : page d'en-têtes hydratée, dossier patient).

## Definition of Done

- [ ] Build passes on api-mail (0 errors)
- [ ] Tests pass (0 failures)
- [ ] Test unitaire : le drain ne dépasse **jamais** `Audit:DrainMaxConnections` bases drainées
      simultanément, quel que soit le nombre de groupes dans le lot (compteur de concurrence
      observé sous un `DrainParallelism` > plafond)
- [ ] Test unitaire : sous plafond atteint, les traces **attendent** (re-spill / lot suivant),
      aucune n'est jetée (`dropped == 0`, invariant task-292)
- [ ] Test : la chaîne de connexion de la route d'audit porte `Application Name=mss-mail-audit`,
      `Connection Idle Lifetime ≤ 30`, `Connection Pruning Interval ≤ 10` ; celle du
      provisionnement porte `Application Name=mss-mail-provision`
- [ ] `observe.ps1` attribue les backends par `application_name` (audit / provision /
      pooler / autre) et non plus par sous-réseau ; fixture + test `report.py` : la colonne
      « directs » n'est plus 0 quand le drain tourne (rejouer le CSV du 11/09 en fixture :
      elle doit rendre > 0 sur la fenêtre 21h17 → 22h05)
- [ ] `report.py` : nouvelle ligne « Coûts résidents » — **backends max / `max_connections`**
      (%), et verdict ROUGE explicite « Postgres à `max_connections` » quand `53300` ou
      backends ≥ 98 % apparaissent (aujourd'hui le rapport les impute au pooler)
- [ ] Aucune donnée de santé en clair dans les nouveaux logs/métriques (noms de bases `u_9…`
      acceptables, jamais d'INS, de RPPS ni de contenu de trace)
- [ ] Documentation : `Api/Mail/docs/ADR-2026-07-27-pgbouncer-transaction-mode.md` (§ risques
      résiduels) et skill `loadtest-skill` (pré-vol : « backends ≪ `max_connections` » et
      « attendre `pg_stat_activity` < 2000 avant `report.sh` »)
- [ ] **Mesure au banc, jambe 1** (journey 1000 iso, Postgres 48 Go, mêmes bases, même SHA
      que la référence 11/09 jambe B pour le reste) : backends max **< 2 300** en régime,
      **0** `53300`, `cl_waiting` < 5 % des relevés, rejeu post-tir sans « too many clients »
      et sans redémarrage de VM ; rapport dans `Docs/audits/`
- [ ] **Mesure au banc, jambe 2** (jambe 1 + un réglage PgBouncer) : backends max
      **< 1 800**, `08P01 = 0`, `cl_waiting = 0` soutenu, erreurs k6 ≤ 0,02 % ; c'est ce tir
      qui rend le **premier verdict SLO opposable à 1000** — rapport dans `Docs/audits/`, ligne
      dans `Api/Mail/tests/loadtest-k6/reports/INDEX.md`

## Manual Test Plan

- **Pré-requis banc** : Postgres 48 Go (task-296), 1000 bases hydratées **gardées**, VM Docker
  Desktop relevée au-delà de 62,8 GiB **ou** conteneurs étrangers au banc arrêtés (sqlserver,
  sonarqube, ollama, pile psc-auth-proxy) — le 11/09 la VM a saturé à 60,7 Go.
- **Lancer** (skill `loadtest-skill`, mode distant) :
  `cd Api/Mail && MSS_LOADTEST=true MSS_ENFORCE_PSC_IDENTITY=false MSS_LOADTEST_MAIL_HOST=192.168.1.69 aspire run --project src/AppHost`,
  pré-vol : `getent ahosts postgres-pgvector` dans PgBouncer → IPv4, `curl 127.0.0.1:9090/-/ready` → 200,
  seed `--users 1000 --messages 0 --mail-host 192.168.1.69 --api http://127.0.0.1:5052 --latency <101−RTT>`.
- **Tir** : `MSS_LOADTEST_MAIL_HOST=192.168.1.69 JOURNEY_STAGES=1000:12600s USERS=1000 MESSAGES_PER_USER=247 UID_BASE=365
  CORPUS_THREAD_SHARE=0.3 JOURNEY_P_TREATMENT=0.095 JOURNEY_P_READ_COLD=0.19 LATENCY_MS=<101−RTT>
  TESTID=journey-1000-task298-leg1-… tests/loadtest-k6/run.sh journey`, `observe.sh start 13500` armé.
- **Ce que l'humain doit voir, pendant la dernière heure** :
  - `docker exec postgres-pgvector psql -U postgres -c "select application_name, count(*) from pg_stat_activity group by 1"` :
    `mss-mail-audit` ≤ 16, total **< 2 300** (jambe 1) puis **< 1 800** (jambe 2), jamais 2 500 ;
  - `docker logs --since 5m postgres-pgvector | grep -c 'too many clients'` → **0** (11/09 : ~1 700/min) ;
  - `SHOW POOLS` : `cl_waiting` = 0, `maxwait` < 1 s, `sv_login` ≈ 0 ;
  - **après le tir** : le rejeu du spill vide Redis (`mss_audit_spill_pending` → 0) **sans** que
    `pg_stat_activity` dépasse 2 300 et sans « too many clients » ; `psql -U postgres` répond à tout moment ;
  - Prometheus : `mss_audit_traces_emitted_total == mss_audit_traces_persisted_total` à la fin, `mss_audit_traces_dropped_total` absent/0 ;
  - rapport : ligne « backends max / max_connections » < 92 %, verdict non ROUGE sur ce motif.
- **Contre-épreuve** (jambe 1) : forcer un rejeu massif — `MSS_LOADTEST_AUDIT_DISABLED` **non** posé,
  couper Postgres 2 min pendant le tir (`docker pause postgres-pgvector`), le rendre : le drain
  rejoue le spill avec ≤ 16 connexions directes simultanées, sans tempête.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — capacité et robustesse d'infrastructure du service MSSanté (EPIC E015)
- **Exigences DSR honorées** : non applicable — aucune exigence DSR ne porte sur le dimensionnement
  des connexions ; la US sert la disponibilité du service au médecin
- **INS** : non applicable — aucune donnée patient manipulée ; le banc n'utilise que des identités
  et des corpus synthétiques
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : le journal d'audit **est** la trace PGSSI-S (task-186/292) — cette US en
  borne le débit de persistance, elle n'en change ni le contenu, ni la rétention (3 653 j accès
  aux données de santé, 365 j technique), ni l'invariant 0 perte ; les refus `53300` sont
  journalisés côté serveur avec `traceId`, sans donnée de santé
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — le réglage du pooler et du drain préfigure Staging/Production
  (portage humain via `DevOps/`) ; aucun nouveau flux, aucune nouvelle donnée
- **AIPD / impact RGPD** : inchangée — même traitement, même finalité, même durée
