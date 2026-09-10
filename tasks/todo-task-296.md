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

- [ ] `DevOps/Dev/PostgreSQL/docker-compose.yml` : `limits.memory` ≥ 24G, `effective_cache_size`
      cohérent (≥ 16GB), `shared_buffers` ≤ 25 % de la limite, `max_connections` inchangé ;
      commentaire daté citant cette US et la mesure d'origine
- [ ] Contrôle post-recréation consigné : `show shared_buffers`, `show effective_cache_size`,
      `docker inspect --format '{{.HostConfig.Memory}}'`
- [ ] Deux tirs journey 1000 iso (12 Go de référence = tir task-292 `fix2` ; jambe A ≥ 24 Go), même
      SHA de code, mêmes bases non purgées, rapports dans `Docs/audits/`
- [ ] Mesure consignée dans cette US : login p95 (référence 10-16 s), backends créés/min,
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
