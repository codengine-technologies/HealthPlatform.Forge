# Campagne de charge — tir `terrain` 1 000 inscrits, cible base de données (2026-09-19)

> Tir `terrain-1000-20260919`, 11:03:46 → 14:04:56 à l'horloge du poste (3 h 01 min 10).
> Harnais : branche `feat/task-321-scenario-terrain` + outillage Postgres du jour (non commité).
> API : `develop` à `2526f413` (task-315 mergée) — **même commit que les 17 et 18/09**. Banc distant `192.168.1.69`.
> Population : celle du 17/09, entièrement hydratée ; aucune purge depuis.
> Rapport : `Api/Mail/tests/loadtest-k6/reports/2026-09-19/report-terrain-1000-20260919-140456.md`
> Photos Postgres : `pgstats-terrain-140458.tsv`, `pgserver-terrain-{debut,fin}-*.tsv`, `pgtables-terrain-{debut,fin}-*.tsv`.

## Ce que ce tir est

**La contre-épreuve du 18/09, instrumentée côté base.** Même population, mêmes gestes, même
rythme `terrain`, même grille SLO, mêmes paramètres (247 messages par boîte, `UID_BASE=365`,
corpus fileté 0,3, latence injectée 96 ms pour un RTT mesuré de 4 à 6 ms, chauffe hydratée).
**Une seule chose change** : le Postgres du banc a été recréé le matin avec
`pg_stat_statements` préchargé et `track_io_timing` actif (cache de pages froid au départ), et
le harnais photographie désormais le serveur SQL avant et après le tir. Objectif : dire, pour la
première fois, **sur quoi** le serveur SQL travaille — et non plus seulement combien.

## Verdict — iso-conditions confirmées : SLO 11/11, 92 actifs

| Grandeur | 18/09 | **19/09** |
|---|---|---|
| Actifs en moyenne (attendu 85) | 93 | **92** |
| Sessions / praticien / h (attendu 0,58) | 0,61 | **0,60** |
| Absence moyenne (attendu 135, transitoire de première absence) | 95 min | **97 min** |
| Débit émergent | 19,8 req/s | **20,4 req/s** |
| Latence moyenne / p95 globales | 267 / 1 141 ms | **255 / 1 117 ms** |
| Erreurs | 0,006 % | **0,012 %** (27 requêtes sur 221 784) |
| Backends Postgres (moy / max) | 231 / 669 | **230 / 676** |
| `cl_waiting` non nul | 1 % des relevés, 7 ms | **1,7 %, pointe à 5 clients** — transitoire d'ouverture |
| Login Postgres p50 / p95 / max | 6 ms | **6 / 7 / 15 ms** |
| CPU hôte (moy / max) | 18,6 % / 81 % | **15,3 % / 96 %** |

Les 11 étapes de la grille sont vertes, avec les mêmes marges qu'hier (page d'en-têtes 144 ms de
p95 pour 1 000 ; fiche patient complète 318 ms pour 4 000). Le rapport titre 🟠 pour trois
raisons dont aucune n'est nouvelle : quatre traitements « verts au SLO mais gros consommateurs »
(dashboard, envoi), l'attente PgBouncer transitoire, et 0,012 % d'échecs — la même famille
IMAP que la veille (`ObjectDisposedException` sur un `ImapClient` en cours d'authentification,
rendue en 500 sur l'ouverture de dossier ; à instruire côté `ImapConnectionService`, hors base).

**Ce que confirme l'iso-conditions** : deux tirs à un jour d'intervalle, même code, même base,
rendent des chiffres à quelques pour cent près. Ce qui suit est donc opposable.

## Ce que le serveur SQL a fait pendant 3 h — première mesure

| Grandeur | Valeur | Lecture |
|---|---|---|
| Transactions validées / s | 468 | pour 20,4 requêtes HTTP/s — **~7 transactions par requête HTTP** (voir F3) |
| Backends actifs (équivalent) | **0,80** | moins d'une requête SQL en exécution à tout instant : Postgres n'est pas le goulet du tir |
| Coût SQL par requête HTTP | **39,3 ms** (37,6 par `pg_stat_statements`) | pour une latence moyenne HTTP de 255 ms |
| Temps SQL cumulé | **139 min** sur 181 | dont **130 min sur deux formes de requête** |
| Taux de cache (blocs) | **93,75 %** | ⚠️ sous 99 % — les lectures hors cache sont les blobs TOAST de F1, pas un cache froid |
| Lecture disque | 5,4 Mo/s, 2,5 % du temps SQL actif | |
| Lignes balayées / renvoyées par index | 82 858 / 13 150 par s (×6,3) | les seq scans dominent sur des tables de 100 à 250 lignes par base — normal à cette taille |
| Écritures | 35 lignes/s, WAL 0,07 Mo/s, 36 checkpoints programmés / 0 forcé | le tir est une charge de **lecture** |
| Interblocages / annulations | 0 / 0,0 % | |
| Croissance des bases praticien | 671 Mo sur 1 000 bases | contenus et PJ remplis à la demande |
| cgroup mémoire Postgres | 99 / 100 % | cache de pages qui prend ce qu'on lui donne (fautes majeures ≤ 3,9/s) |

Réglages : PostgreSQL 16.11, `shared_buffers` 12 Go, `effective_cache_size` 36 Go, `work_mem`
4 Mo, `random_page_cost` 4.0, `max_connections` 2 500.

## Findings

### F1 — 🔴 La page d'en-têtes charge les blobs qu'elle n'affiche pas : 93,6 % du temps SQL

Deux formes de requête portent **130 des 139 minutes** de temps serveur SQL du tir :

| # | Forme | Appels | ms / appel | Lignes / appel | Blocs / appel | Hors cache | Part |
|---|---|---|---|---|---|---|---|
| 1 | `SELECT m.* , (count biologie), (count synthèse) FROM "MailMedicalDocuments" m WHERE m."MailId" = ANY($1)` | 28 405 | **141** | 17 | 686 | 15 % | **48,0 %** |
| 2 | `SELECT m."Id", m."Content", … FROM "MailAttachments" m WHERE m."MailId" = ANY($1)` | 28 404 | **134** | 28 | 491 | 20 % | **45,6 %** |

**Le plan n'est pas la cause.** `explain (analyze, buffers)` sur la base praticien la plus
volumineuse (243 PJ, 145 documents) rend ces deux requêtes en **0,2 et 0,5 ms** pour une page de
25 mails : le balayage séquentiel est le bon plan à cette taille. **Le coût est le volume
détoasté et transféré** :

| Colonne | Taille moyenne (base échantillon) | Par appel |
|---|---|---|
| `MailAttachments.Content` (bytea) | **182 Ko** | 28 lignes ≈ **5,1 Mo** |
| `MailMedicalDocuments.HtmlBody` | **222 Ko** | 17 lignes ≈ **3,8 Mo** |
| `MailMedicalDocuments.Embedding` (vecteur) | 6 Ko | (inclus) |
| `MailMedicalDocuments.Body` | 3,9 Ko | (inclus) |

**~9 Mo par page de 25 en-têtes**, lus dans le TOAST (d'où les 15 à 20 % hors cache et le taux
de cache global de 93,75 %), transmis à api-mail, désérialisés en entités EF, puis **jetés** : la
page d'en-têtes n'affiche ni le contenu d'une PJ ni le HTML d'un document.

**Attribution par lecture du code** : `LoadBulkMailLookupsAsync`
(`Api/Mail/src/Infrastructure/Repositories/MailDb/MailRepository.cs:1412`) matérialise les
entités entières — `db.MailAttachments.Where(a => mailIds.Contains(a.MailId)).ToListAsync()` et
`db.MailMedicalDocuments.Where(…).Select(d => new { Doc = d, BiologyCount = …, SummaryCount = … })`
— y compris en mode `MailBuildType.Header`. Appelants pendant le tir : la page d'en-têtes
`GET …/emails/{ids}` (`read_list`/`emails`, 15 615 appels) et `GetMailAsync(Header)` derrière
« marquer lu » (12 428 appels) : 28 043 ≈ 28 405.

**Remède** : deux projections en mode Header — PJ : `Id, MailId, FileName, ContentType, Size,
Guid, DocumentId` (sans `Content`) ; documents : toutes les colonnes de métadonnées, sans
`HtmlBody`, `Body`, `Embedding`, `MetadataJson`. Aucun changement de contrat DTO.
**Gain attendu** : SQL par requête HTTP **37,6 → ~3 ms** ; taux de cache **≥ 99 %** ; lecture
disque ÷ 5 ; et côté api-mail, 9 Mo d'allocations en moins par page (le gain mémoire de task-194
était de cette nature). **Risque** : un champ du DTO d'en-tête qui lirait l'une de ces colonnes —
à vérifier dans `BuildMailDto` avant de projeter. **Preuve attendue** : ligne `POSTGRES-INDEX.md`
d'un tir `terrain` 1000 iso-conditions.

### F2 — 🟠 Aucun index sur `MailId` pour `MailAttachments` ni `MailMedicalDocuments`

Seq scans mesurés sur la base échantillon pendant le tir : 91 (`MailAttachments`) et 73
(`MailMedicalDocuments`). Seuls existent la clé primaire et, pour les documents, des index sur
`PractitionerContactId`, `DuplicateOfId`, `SupersededByDocumentId`, `SetId`,
`SuppressionRequestedByMailId` et le composite `(Ins, MailId, Date)` — inutilisable pour un
filtre sur `MailId` seul. Coût négligeable aujourd'hui (150 à 250 lignes par praticien), il
**croît avec l'ancienneté de la boîte**. Une migration EF, deux index — **après F1** : F1 est le
coût, F2 la marge.

### F3 — 🟡 Sept transactions SQL par requête HTTP

`DISCARD ALL` — le reset que PgBouncer joue à chaque libération d'une connexion serveur —
compte **1 594 911 appels pour 221 784 requêtes HTTP** (7,2 par requête), et le registre
(`mss_accounts`, base unique) est lu **3 fois par requête** (662 950 × 2 + 221 781, 0,03 ms
chacune). Ensemble 0,6 % du temps SQL : ce n'est pas un coût, c'est un **témoin** — la page
d'en-têtes émet ~7 requêtes SQL indépendantes (tags, destinataires, PJ, contenus enrichis,
fils, documents, doublons), chacune dans sa transaction pooler. Regrouper viendra après F1 ;
mettre le registre en cache par requête (3 lectures identiques) est un geste court.

### F4 — Instrument : trois corrections faites pendant le tir, deux à faire avant le prochain

- **`queryid` diffère par base.** `pg_stat_statements` calcule le `queryid` sur l'arbre
  d'analyse, OID des tables compris : la même requête EF portait 1 000 identifiants sur 1 000
  bases, et seules les requêtes du catalogue s'agrégeaient. L'agrégation se fait désormais sur
  le **md5 du texte normalisé** (`pg-statements.sh`), corrigé à 12:05, avant la photo de fin.
- **Plafond d'entrées atteint** : 48 211 entrées pour `pg_stat_statements.max = 50 000`,
  **22 évictions** pendant le tir — les formes rares sont sous-comptées, le top 20 reste fiable.
  Porter `pg_stat_statements.max` à **100 000** avant le prochain tir 1000 (compose DevOps).
- **382 Mo de fichiers temporaires attribués à tort au tir** : ils appartiennent à la base de
  maintenance `postgres`, où tournaient les requêtes d'agrégation de l'outil lui-même (48 000
  lignes triées sous `work_mem` 4 Mo). La photo serveur exclut désormais cette base ; le rapport
  du jour porte encore le chiffre brut, annoté.
- **Statistiques de tables périmées** : `n_live_tup = 0` sur des tables pleines (jamais
  d'`ANALYZE` depuis la dernière remise à zéro) — le critère « index candidat » accepte la
  taille de la table comme second témoin. Un `ANALYZE` par base hydratée, ou `autovacuum`
  laissé faire, rendrait `pg_stat_user_tables` lisible.

### Mesures complémentaires (après le tir, banc arrêté, statistiques du tir conservées)

**La part TOAST est mesurée, plus seulement déduite** (`pg_statio_user_tables`, base échantillon,
cumul du tir) : les blocs de **tas** de `MailAttachments` et `MailMedicalDocuments` sont servis en
cache à plus de 97 %, leurs blocs **TOAST** (les blobs) sont lus sur disque à **34 %** et **44 %**.
Le taux de cache global de 93,75 % est donc entièrement celui des blobs de F1 ; le reste de la base
tient en mémoire.

**Le temps SQL par geste du parcours** (formes regroupées par nombre d'appels ≈ nombre d'appels
k6 du geste) :

| Geste (appels k6) | Formes SQL | Temps SQL | Part | Lecture |
|---|---|---|---|---|
| Page d'en-têtes + marquer lu (~28 400) | 9 | **130,4 min** | **93,8 %** | F1 : deux formes à 141 et 134 ms, les sept autres à moins de 0,15 ms |
| Recherche (2 × 13 398 `ILIKE` sur `Body`) | 2 | 4,1 min | 2,9 % | 9 ms par forme, balayage `MailContents` / `MailMedicalDocuments` — second poste, marginal |
| Arrivée dashboard (~62 500 × 8 formes par mail) | 8 | 1,5 min | 1,1 % | un lot de requêtes **par mail** (`WHERE "MailId" = $1`), à 0,03–1 ms : un N+1 sans coût aujourd'hui, et déjà **projeté** (`SELECT "FileName", "ContentType", "Size" FROM "MailAttachments"`) — la preuve que la projection de F1 existe déjà ailleurs dans le code |
| Dossier patient / recherche vectorielle (~3 000–4 000) | 10 | 0,5 min | 0,3 % | pgvector `<=>` à 2,5 ms sans index, chargement du catalogue de types Npgsql à chaque connexion physique (3 994) |
| Marquer lu (écritures `PendingActions`, ~11 400 × 4) | 4 | 0,1 min | — | insert + update + delete + select par action : trois écritures pour un geste, sans coût |
| Fiche patient / documents (~50 700) | 2 | 0,0 min | — | **aucune requête SQL métier** : `BEGIN`/`COMMIT` seuls — le geste est servi hors base (cache, IMAP) |
| Contrôles de schéma à la connexion (`information_schema.columns`, 6 688 × 1,1 ms) | 2 | 0,1 min | — | une vérification de colonne par ouverture de base — à cacher par base, sans urgence |

Ce tableau est la réponse à « où va le temps SQL d'un praticien » : **tout dans un seul geste**, et
dans ce geste, tout dans deux colonnes.

### Ce qui n'est PAS un finding base de données

- **`dashboard`** (47,8 % du temps serveur k6) : ses quatre appels sont IMAP (`folder` 433 ms
  de p50 = ouverture de dossier), pas SQL. **`send`** (15,7 %) : IMAP/SMTP (archivage Sent).
- La **recherche texte** (`ILIKE` sur `MailContents.Body`, 9 ms par appel, 1,5 %) et la
  **recherche vectorielle** (pgvector `<=>`, 3 ms, 0,1 %) ne pèsent rien à 150 documents par
  praticien ; l'index GIN / HNSW n'est pas un sujet à cette taille.
- Les **backends** (230 en moyenne, 676 au pic) suivent le nombre de bases touchées, pas la
  charge SQL — 0,80 requête en exécution en moyenne. Le pooler est dimensionné pour la
  population, pas pour le travail.

## Ce que ce tir établit, et ce qu'il n'établit pas

**Établi.**
1. Postgres **n'est pas le goulet** du parcours terrain à 1 000 inscrits : 0,8 requête active
   en moyenne, login à 6 ms, 0 refus, 0 interblocage, WAL négligeable.
2. Le temps SQL est **concentré à 93,6 % sur une cause unique et mesurée** (F1), dont le
   remède est une projection EF — sans changement de contrat ni de schéma.
3. Le rapport porte désormais la **réaction du serveur SQL** de façon comparable
   (`POSTGRES-INDEX.md`, première ligne) : le prochain tir dira si F1 a payé.

**Non établi.**
1. Le gain de F1 sur la **latence ressentie** : 141 + 134 ms de SQL par page pour un p50 de
   96,6 ms sur `emails` — les deux requêtes tournent donc **en parallèle** de l'IMAP ou entre
   elles ; le gain visible du praticien peut être inférieur au gain serveur. À mesurer.
2. La part exacte du **TOAST** dans le taux de cache : déduite (15 à 20 % hors cache sur les
   seules formes F1), non mesurée par `pg_statio_user_tables`.
3. Les **formes rares** (22 évictions) et tout ce que la base `postgres` de maintenance a
   masqué — corrigés pour le prochain tir, pas pour celui-ci.

## Axes proposés — à arbitrer

1. **US F1 + F2** : projections Header + deux index `MailId`, A/B `terrain` 1000 iso-conditions.
2. **Registre en cache par requête** (3 lectures identiques de `mss_accounts` par requête HTTP).
3. **Instrument** : `pg_stat_statements.max` 100 000 ; `ANALYZE` des bases hydratées avant un
   tir ; publier la part TOAST via `pg_statio_user_tables` dans la photo des tables.
4. **`ImapConnectionService`** : `ObjectDisposedException` sur un client en cours
   d'authentification, deux tirs de suite — un défaut de cycle de vie, hors base.

## Réserves

- Harnais sur branche non mergée (PR #245) et outillage Postgres du jour **non commité**
  (`pg-statements.sh`, `report_postgres.py`, `report.sh`, `run.sh`, compose DevOps).
- Cache de pages froid au départ (conteneur recréé) : la première heure lit plus sur disque que
  le 18/09 ; la chauffe hydratée n'a pas suffi à le remplir (cgroup à 99 % dès la mi-tir).
- Analyse Seq par échantillonnage (API `/api/data` sous session, MCP tronqué) : une famille
  d'erreurs vue, aucun dénombrement exhaustif.
- Bases praticien **non purgées** en fin de tir, délibérément : iso-conditions pour l'A/B F1.
