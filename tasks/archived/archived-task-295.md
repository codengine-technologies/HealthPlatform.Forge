# todo-task-295.md — Le banc mesure le coût d'ouverture d'une connexion PostgreSQL et le churn des backends : lire la corrélation « login lent ⇒ `sv_login` ⇒ refus » au lieu de la déduire

**Repos**: api-mail
**Dependencies**: —
**Epic**: E015
**Single frontend**: true
**Priorité**: **1** — préalable aux jambes A/B de `task-294` (PgBouncer « attendre au
lieu de rejeter ») et au redimensionnement mémoire du Postgres du banc : sans cette
mesure, aucune de ces jambes ne peut dire **pourquoi** les refus tombent ou persistent.

> **Origine** : analyse d'architecture de la connexion PostgreSQL du 2026-09-09
> (`Docs/plan_remediation_fable.md`, phase 0). Le diagnostic du `08P01 connect timeout
> (server_login_retry)` tient sur trois maillons mesurés **à la main** pendant les tirs des
> 08/09 et 09/09 : login d'un backend à 10-16 s (un `psql` chronométré dans le conteneur),
> ~15 ouvertures de backends par seconde demandées pour ~3,8 servies (`sv_login` 212-243),
> cgroup mémoire du conteneur à 99,9 % de sa limite. Aucune de ces trois grandeurs n'est
> relevée par le harnais : `observe.ps1` ne sonde que le total des backends et la part sur
> bases praticien, et `report.py` ne connaît que `cl_waiting` / `maxwait` (et, depuis
> `task-294`, `sv_login` et les refus). Le verdict d'un tir rouge reste donc une **déduction**
> reconstituée après coup, jamais une **lecture** sur une même série temporelle.

## Objective

Que chaque tir du banc publie, sur la même grille de temps que `cl_waiting` et les refus
PgBouncer, **ce que coûte l'ouverture d'un backend Postgres et à quel rythme le système en
ouvre**, pour que le rapport puisse dire : « les refus apparaissent quand le login dépasse
N s », ou « les refus apparaissent avec un login sain : la cause est ailleurs ».

Ce que le rapport doit rendre lisible, à N médecins :

1. **Le coût d'un login** — durée, en secondes, d'une connexion sonde à une base praticien
   (ouverture + `select 1`), relevée à chaque échantillon depuis le conteneur Postgres, donc
   **sans** PgBouncer entre les deux : c'est le coût que PgBouncer paie lui-même quand il
   ouvre un backend. Référence saine mesurée le 09/09 au soir : **6 ms**. Pendant l'incident :
   **10 à 16 s**, au-dessus du `server_connect_timeout` de 15 s.
2. **Le débit de création de backends** — nombre de backends dont le `backend_start` date de
   moins de 60 s, par relevé. C'est le « débit de création de connexions », à opposer au
   « débit de requêtes » : c'est lui qui gouverne l'incident, pas les req/s.
3. **La survie des backends à l'idle** — nombre de backends `idle` depuis plus de 60 s. Zéro
   soutenu signifie que **tous** les backends inactifs sont recyclés (churn total), ce que
   `server_idle_timeout = 60` produit sur 1000 pools. Ce compteur est le témoin direct de la
   jambe `server_idle_timeout` de `task-294`.
4. **La part des routes directes** — backends venant du réseau Docker du pooler vs backends
   directs (provisionnement, sonde de santé, journal d'audit depuis `task-292`). Le
   commentaire de `AuditTraceRepository` affirme que les backends directs « ne suivent pas
   la population » ; c'est vrai par base, **non mesuré en agrégat** (borne théorique :
   groupes drainés/s × 60 s × réplicas).
5. **La pression mémoire du conteneur Postgres** — usage et limite du cgroup, cache de pages,
   RSS, et **fautes majeures par seconde** (delta du compteur `pgmajfault`). C'est la
   grandeur qui explique le login lent : à 58 Go de bases pour 12 Go de cgroup, chaque
   backend retenu (~2,3 Mo) est pris sur le cache de pages, et le login lit le catalogue
   sur disque.
6. **Le verdict** — le rapport avertit quand le login dépasse **1 s** ou quand `sv_login`
   dépasse **20** de façon soutenue, et publie ces grandeurs dans « Coûts résidents contre N »
   à côté de `cl_waiting`. Il ne **classe pas** le tir ROUGE sur ces seuls seuils : un login
   lent sans refus est une **alerte** (le système tient encore), un refus est déjà ROUGE
   depuis `task-294`.

### Ce que ce n'est pas

- **Pas de réglage** de PgBouncer ni de Postgres : c'est `task-294` (pooler) et un acte
  humain sur `DevOps/` (mémoire du conteneur). Cette US ne fait que **voir**.
- **Pas de nouvelle métrique applicative** côté `api-mail` : tout se relève depuis le banc
  (`docker exec` dans les conteneurs), comme les sondes existantes.
- **Pas d'alourdissement du tir** : une connexion sonde par relevé (toutes les 10 s) et
  quatre requêtes `pg_stat_activity` légères. Le `docker exec` coûte déjà ; la cadence de
  `observe.ps1` est tenue par soustraction du temps passé (mécanisme existant). Si la sonde
  de login elle-même dépasse l'intervalle (login à 15 s), l'échantillon porte la valeur
  mesurée et le relevé suivant repart sans rattrapage.

### Décisions déjà prises (ne pas rouvrir)

- La sonde de login se fait **depuis le conteneur Postgres** (`psql` local), pas depuis
  PgBouncer ni depuis l'hôte : on mesure le coût du serveur à créer un backend, sans réseau
  ni pooler. La base cible est une base praticien **fixe** pour tout le tir (choisie au
  premier relevé parmi `u\_%`), afin que la série soit comparable d'un relevé à l'autre.
- L'origine « pooler » d'un backend se lit sur `client_addr` : le réseau Docker du pooler
  (`172.x`) vs tout autre (hôte, `local`). C'est une convention de banc, documentée dans
  la sonde, pas une propriété de l'application.
- Les compteurs cgroup se lisent en v1 (`/sys/fs/cgroup/memory/memory.*`), qui est ce que
  le conteneur expose sur ce poste ; la sonde tolère l'absence des fichiers (v2 ou autre
  hôte) et **n'émet alors aucun échantillon** plutôt qu'un zéro trompeur.

## Definition of Done

- [ ] Build passes on api-mail (0 errors)
- [ ] Tests pass (0 failures)
- [ ] `observe.ps1` — `Sample-Postgres` publie, par relevé, les échantillons
      `postgres/login/seconds`, `postgres/backends/started_last_60s`,
      `postgres/backends/idle_over_60s`, `postgres/backends/pooler`,
      `postgres/backends/direct`, `postgres/cgroup/usage_pct`, `postgres/cgroup/cache_mb`,
      `postgres/cgroup/rss_mb`, `postgres/cgroup/majfault_per_s` (delta entre deux relevés,
      absent au premier) ; une sonde en échec ne coûte jamais la ligne des autres
      (`Write-ProbeFailure`, mécanisme existant)
- [ ] `observe.ps1` — la base cible de la sonde de login est fixée au premier relevé et
      journalisée ; aucune donnée de santé dans le journal (le nom `u_9…` est acceptable)
- [ ] `report.py` — « Coûts résidents contre N » porte, par palier : login p50 / p95 / max
      (s), `started_last_60s` moyen / max, `idle_over_60s` min, backends `pooler` / `direct`
      max, cgroup usage max (%), `majfault_per_s` moyen / max
- [ ] `report.py` — avertissement (pas ROUGE) « ⚠️ login PostgreSQL > 1 s » si le p95 du
      palier dépasse 1 s, et « ⚠️ `sv_login` > 20 soutenu » si `sv_login` dépasse 20 sur
      plus de 50 % des relevés du palier ; les deux textes renvoient à `task-294` et à
      `Docs/plan_remediation_fable.md`
- [ ] `report.py` — une ligne de conclusion **corrèle** : « refus PgBouncer présents ET login
      p95 > 1 s : le login lent est la cause probable » / « refus présents ET login p95 < 1 s :
      la cause n'est pas le login, lire `SHOW LISTS` et le DNS » / rien si aucun refus
- [ ] Tests Python : `test_report_resources.py` étendu (nouvelles lignes, palier sans
      échantillon cgroup → lignes absentes, pas de zéro), `test_report_conclusions.py`
      étendu (les trois branches de la corrélation), fixtures `observe-login-*.csv`
      ajoutées ; `tests/loadtest-k6/selftest.sh` vert
- [ ] `tests/loadtest-k6/README.md` — section « Ce que mesure le banc côté PostgreSQL »
      décrivant les 9 échantillons, leur lecture, et la référence saine (login 6 ms)
- [ ] Un tir court (200 praticiens, ≥ 20 min, `journey`) rejoué : les 9 colonnes présentes
      sans trou sur toute la fenêtre, rapport `.md` produit, ligne `INDEX.md`
- [ ] Aucune donnée de santé dans les nouveaux logs / échantillons / rapport (noms de bases
      `u_9…` acceptables, jamais d'INS ni d'adresse)

## Manual Test Plan

- **Banc** (skill `loadtest-skill`) :
  `cd Api/Mail && MSS_LOADTEST=true MSS_ENFORCE_PSC_IDENTITY=false aspire run --project src/AppHost`,
  seed `--users 200 --messages 0 --api http://127.0.0.1:5052`. Bases gardées.
- **Tir court** : `JOURNEY_STAGES=200:1200s USERS=200`, `observe.ps1` lancé par `run.ps1`
  comme d'habitude.
- **Pendant le tir**, l'humain ouvre le CSV d'observation et doit voir, à chaque relevé :
  - une ligne `postgres;login;seconds;…` avec une valeur de l'ordre de **0,005 à 0,05** sur
    un Postgres sain ;
  - `postgres;backends;started_last_60s` non nul pendant la montée, puis qui baisse en régime ;
  - `postgres;backends;idle_over_60s` à **0** tant que `server_idle_timeout = 60` (branche
    `develop`) — c'est le témoin du churn ;
  - `postgres;backends;pooler` et `postgres;backends;direct`, dont la somme ≈
    `postgres;backends;total` ;
  - `postgres;cgroup;usage_pct` et `postgres;cgroup;majfault_per_s` (absent au premier relevé).
- **Contre-épreuve du seuil** : pendant le tir, l'humain impose une lenteur artificielle du
  login en saturant la mémoire du conteneur (par exemple `docker update --memory 3g
  postgres-pgvector` **sur le banc uniquement**, puis retour à `12g`) ; le rapport doit
  publier « ⚠️ login PostgreSQL > 1 s » sur le palier concerné. Si des refus PgBouncer
  apparaissent, la ligne de corrélation « login lent est la cause probable » doit être
  présente.
- **Contre-épreuve de la tolérance** : `observe.ps1` lancé sur un poste sans cgroup v1
  (ou fichiers absents) ne doit produire **aucune** ligne `postgres;cgroup;*`, et le rapport
  ne doit pas afficher de ligne cgroup pour ce palier.
- **Rapport** : `report.py` sur le tir → section « Coûts résidents contre N » avec les
  nouvelles lignes, aucun avertissement sur un banc sain, `INDEX.md` mis à jour.
- **Rendre le banc** (étape 6 du skill), bases gardées.
- **Données de test** : synthétiques uniquement (praticiens `u_9…`, aucun patient).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — outillage de mesure du banc de charge (EPIC E015), aucune
  fonctionnalité exposée au PS
- **Exigences DSR honorées** : non applicable — aucune exigence DSR ne porte sur le harnais
  de test ; la US sert la disponibilité du service MSSanté en rendant ses pannes lisibles
- **INS** : non applicable — aucune donnée patient manipulée ; le banc ne porte que des
  praticiens synthétiques
- **Authentification PS** : inchangée — la sonde s'authentifie sur le Postgres du banc avec
  les identifiants synthétiques du banc, jamais sur un environnement HDS
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : non applicable — les échantillons relevés (durées, compteurs de
  backends, mémoire) ne sont pas des évènements métier ; ils ne contiennent aucune donnée
  de santé
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non — banc local de développement ; les sondes sont conçues pour
  être portées telles quelles en Staging (non HDS) par l'équipe système, hors forge
- **AIPD / impact RGPD** : inchangée — aucun traitement de données personnelles

## Branches
- `api-mail` (pushed) : feat/task-295-bench-postgres-login-probe — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-295-bench-postgres-login-probe
- `dtos-mss` (pushed, auto-included) : feat/task-295-bench-postgres-login-probe — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-295-bench-postgres-login-probe

## Timings

*(généré par `tools/timing/report.sh --task task-295 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 15 s | — | — | — | — |
| /develop | ok | 23 min 41 s | 1 (10 s) | 4 (3 min 44 s) | — | api-mail 1B/4T |
| /sonar | ok | 16 min 23 s | 3 (55 s) | 12 (5 min 27 s) | 2 (1 min 07 s) | 2 itération(s), api-mail 3B/12T |
| /lint-angular | skipped | 0.5 s | — | — | — | client-angular hors Repos ; arbre de travail = WIP humain (environment.ts) sans rapport |
| /lint-mobile | skipped | 0.7 s | — | — | — | client-mobile hors Repos, arbre propre sur develop |
| /verify-visual | skipped | 0.7 s | — | — | — | aucun écran mobile touché (pas de Stitch design log, client-mobile hors Repos) |
| /review | ok | 7 min 31 s | 2 (22 s) | 1 (1 min 40 s) | — | api-mail 2B/1T |
| /tech-writer | ok | 4 min 05 s | — | — | — | — |
| **Total cycle** | | **51 min 58 s** | **6 (1 min 28 s)** | **17 (10 min 52 s)** | **2 (1 min 07 s)** | |

## Develop log

- Repos touched : `api-mail` (harnais du banc `tests/loadtest-k6/` uniquement — aucun code C# applicatif)
- DTOs published : no DTO change (`dtos-mss` : branche vide, aucun commit)
- Interop published : no interop change
- Commits :
  - api-mail : 82eaf3c feat(loadtest): le banc lit le coût du login PostgreSQL et le churn des backends au lieu de les déduire (task-295)
  - api-mail : 7c0a31e refactor(loadtest): simplify pass (/simplify) — task-295
- Ce qui a été livré :
  - `observe.ps1` — trois sondes **séparées** (une sonde en échec ne coûte jamais la ligne des autres) : `Sample-Postgres` étendu (`started_last_60s`, `idle_over_60s`, `pooler`/`direct` par `client_addr`, même requête `pg_stat_activity`, sonde exclue par `pg_backend_pid`) ; `Sample-PostgresLogin` (psql **dans** le conteneur, chronomètre `bash $EPOCHREALTIME` en µs — le `date` busybox de l'image Alpine ignore `%N` ; base praticien `u_9…` fixée au premier relevé et journalisée) ; `Sample-PostgresCgroup` (cgroup v1 : `usage_pct`, `cache_mb`, `rss_mb`, `majfault_per_s` en delta absent au premier relevé ; fichiers absents → **aucun** échantillon, journalisé une fois). Helper `Invoke-ContainerScript` : PowerShell 5.1 ne protège pas les `"` d'un argument natif (sonde muette constatée à la première exécution) → refus bruyant de tout script shell qui en contient.
  - `report.py` — « Coûts résidents contre N » : login p50 / p95 / max (s), `started_last_60s` moy/max, `idle_over_60s` min, `pooler`/`direct` max, cgroup usage max (%) et `majfault_per_s` moy/max (lignes cgroup **absentes** sans échantillon, jamais à zéro) ; avertissements `⚠️ login PostgreSQL > 1 s` et `⚠️ sv_login > 20 soutenu` (jamais ROUGE) renvoyant à task-294 et `Docs/plan_remediation_fable.md` ; ligne de corrélation à trois branches (cause probable / cause ailleurs → `SHOW LISTS` + DNS / login non relevé → corrélation impossible), reprise dans le motif ROUGE du verdict.
  - Tests : `test_report_resources.py` +10 (quantiles, sustained, lignes, cgroup absent, avertissements), `test_report_conclusions.py` +6 (trois branches + verdict + login lent seul non ROUGE) ; fixtures `observe-login-slow.csv`, `observe-login-healthy-refusals.csv`, `observe-login-sain.csv`.
  - `README.md` — section « Ce que mesure le banc côté PostgreSQL (task-295) » : les 9 échantillons, leur lecture, la référence saine (6 ms).
- Validation live (poste local, conteneur `postgres-pgvector` seul) : les 11 métriques `postgres/*` sortent ; login mesuré **5,1 à 7,6 ms** (référence saine 6 ms) ; cgroup 79,7 → 93,8 % ; `majfault_per_s` absent au premier relevé puis 0.
- Local build / test : ✓ api-mail `dotnet build` 0 erreur 0 warning ; `dotnet test` 4 354 réussis (16 skip pré-existants) ; `selftest.sh` ✅ 354 tests (node + unittest)
- Passe qualité (/simplify) :
  - Applied & committed : api-mail: 2 files (7c0a31e) — `sustained_share` réutilisé pour `sv_login` ; spec de lignes générale `(scope, target, metric, label, stat, digits)` rendue par une seule boucle (login inclus, `max_pct` supprimé) ; libellés de seuil dérivés des constantes ; corrélation calculée une fois dans `run_verdict` ; `Invoke-ContainerScript` + `ConvertTo-Doubles` dans `observe.ps1`
  - Skipped (notés) : fusion cgroup → `Sample-Postgres` (−200 ms/relevé) refusée — la séparation des sondes est une décision de la US ; migration de `started_last_60s` vers `JOURNEY_RESIDENT_KEYS` refusée — la juxtaposition login/churn sous la ligne de refus est voulue ; `Invoke-PostgresSql` non extrait (toucherait `Sample-Postgres`/`Sample-PgBouncer` hors diff)
  - Skipped (contract/excluded) : dtos-mss
- DOD self-check : 9/10 items vérifiables satisfaits (build, tests, 9 échantillons `observe.ps1`, base cible fixée + journalisée, lignes `report.py`, avertissements, corrélation, tests Python + fixtures + `selftest.sh`, README, aucune donnée de santé — seuls des noms `u_9…`). **1 item de banc différé (HAG)** : tir court 200 praticiens ≥ 20 min `journey` avec les 9 colonnes sans trou + rapport + `INDEX.md` — nécessite l'AppHost en profil loadtest et un seed (skill `loadtest-skill`), hors portée d'un `/develop` ; le Manual Test Plan le décrit.
- Next step : /sonar task-295

## Sonar log

- Phase 1 (new code) : ✓ Quality Gate **OK**, `new_coverage` = 91,5 %, **0** issue new-code, **0** hotspot new-code
- Phase 1 — Issues fixées : **2** (code smells `CA1869`, sévérité INFO — `JsonSerializerOptions` construit par appel dans `AuditBackgroundServiceFallbackTests`, new code hérité de task-292)
- Phase 1 — Tests ajoutés : 0 (aucune ligne de C# écrite par cette task — le livrable est le harnais Python/PowerShell du banc)
- Phase 2 (legacy) : **skippée** — 3 des 4 cibles dures d'`agents/sonar-targets.yml` sont déjà tenues (`bugs` 0, `vulnerabilities` 0, `sqale_rating` A) et la task n'écrit aucun C# : nettoyer 59 smells legacy sans rapport aurait fait exploser le périmètre de la PR (règle des ~30 fichiers). Phase 2 est best-effort et ne bloque jamais le cycle.
- Phase 2 — Issues restantes : 59 code smells + 3 security hotspots (dette pré-existante, acceptée)
- Build / tests : ✓ green (Release, 5 suites OpenCover, 4 354 tests réussis)
- Conteneur SonarQube : redémarré par le pré-flight (`sonarqube_db` puis `sonarqube`), version **9.9.8.100196** → propriété `sonar.login`, port publié **9000** (et non 9001 : `docker port sonarqube` fait foi, cf. l'encadré d'`agents/sonar.md`)

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | **OK** | → |
| New coverage | 88,0 % | **91,5 %** | +3,5 pt |
| New code smells | — (2 au 1er scan de ce run) | **0** | −2 |
| New bugs / vulnerabilities / hotspots | 0 / 0 / 0 | **0 / 0 / 0** | → |
| Bugs | 0 | 0 | → |
| Vulnerabilities | 0 | 0 | → |
| Security hotspots | 3 | 3 | → |
| Code smells | 59 | 59 | → (61 au 1er scan, −2 par le fix CA1869) |
| Coverage (projet) | 88,1 % | **88,6 %** | +0,5 pt |
| Duplication | 0,4 % | 0,4 % | → |
| Reliability / Security / Maintainability | A / A / A | **A / A / A** | → |

> **Note sur `new_coverage` (91,5 % vs cible 95 % d'`agents/sonar-targets.yml`)** : la
> période « new code » du projet est `PREVIOUS_VERSION` — elle couvre donc tout le C#
> mergé par task-292 / 293 / 294 ce matin, pas le diff de task-295. **Cette task n'ajoute
> aucune ligne de C#** (le livrable est `tests/loadtest-k6/`, du Python et du PowerShell) :
> l'écart de couverture ne lui appartient pas et ne peut pas être comblé depuis son
> périmètre. La condition `new_coverage` du Quality Gate est **OK**.

- Convention alimentée : `conventions/csharp.md` — nouvelle entrée **CA1869** (`JsonSerializerOptions` partagé, jamais une instance par appel ; vaut aussi dans les tests), `Occurrences : 1`
- Next step : /lint-angular task-295

## Lint log

- **Skippée proprement** — `client-angular` n'est pas dans les `**Repos**:` de la task (`api-mail` seul) et `/develop` n'a écrit aucune ligne d'Angular.
- Contrôle de l'arbre de travail Angular : 2 fichiers modifiés (`front/apps/mss/src/environments/environment.ts`, `front/apps/weda2/src/environments/environment.ts`), sur la branche **`feature/nova-rewriting-mss`** de l'humain. Ce sont ses URL d'API locales (`https://mss-api.xsd2code.com` → `https://localhost:7012`), sans aucun rapport avec task-295 : la forge n'y touche pas (mode code-only, l'humain est maître de sa branche et de son arbre).
- Itérations consommées : 0 / 5
- Next step : /lint-mobile task-295

## Lint mobile log

- **Skippée proprement** — `client-mobile` n'est pas dans les `**Repos**:` de la task (`api-mail` seul), l'arbre de travail de `Client/Mobile/` est propre et sur `develop` (aucun diff vs `origin/develop`).
- Itérations consommées : 0 / 5
- Next step : /verify-visual task-295

## Visual verify log

- **Skippée proprement** — aucun écran `client-mobile` touché : la task ne liste que `api-mail` dans ses `**Repos**:`, il n'y a pas de `## Stitch design log`, et `Client/Mobile/` est propre sur `develop`. Aucune capture à prendre, aucun serveur `ng serve` démarré.
- Next step : /review task-295

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/228 — label `awaiting-human-merge`
- `dtos-mss` : aucun commit sur `feat/task-295-bench-postgres-login-probe` (pas de changement de contrat) — pas de PR

## Code Review Summary

**Verdict : APPROVED** — 0 blocage, **2 défauts trouvés et corrigés avant la PR**, 2 suggestions non bloquantes.

### Défauts trouvés et corrigés

1. **Le chronomètre rendait toujours 0** (trouvé en exécutant la sonde, pas en la relisant). Le `date +%N` de l'image **Alpine** (busybox) du Postgres du banc ignore les nanosecondes : un login de 6 ms se lisait « 0 s ». Remplacé par `$EPOCHREALTIME` de bash 5, présent dans l'image. Sans cette exécution réelle, la task aurait livré une sonde qui publie une colonne de zéros — c'est-à-dire exactement le mode d'échec silencieux qu'elle existe pour empêcher.
2. **La sonde redéfinissait un compteur historique** (trouvé en revue de code, commit `303eb98`). Le `where backend_type = 'client backend' and pid <> pg_backend_pid()` était **global** : il retranchait aussi les processus d'arrière-plan (checkpointer, walwriter, autovacuum…) de `backends/total` et `practitioner_databases`, deux séries comparées d'une campagne à l'autre depuis task-204. Mesuré sur le banc au moment de la revue : `total` serait passé de **566 à 560** — six processus perdus en silence, donc toute comparaison avec un tir archivé faussée sans que rien ne le signale. Le filtre vit désormais dans les `filter (where …)` des quatre nouveaux compteurs seuls.

### Par fichier

- `tests/loadtest-k6/observe.ps1` — ✅ l'isolation des sondes (« une sonde en échec ne coûte jamais la ligne des autres ») est respectée : trois fonctions séparées, chacune avec son `try/catch` et son `Write-ProbeFailure`. `Invoke-ContainerScript` encapsule le piège PowerShell 5.1 des guillemets doubles et **refuse bruyamment** un script qui en contient. Sentinelle de limite cgroup (`< 1e18`) et compteur qui recule (conteneur recréé) tous deux gardés.
- `tests/loadtest-k6/report.py` — ✅ `sustained_share` (task-212) réutilisé au lieu d'être réimplémenté ; absence et zéro restent distincts partout (`NOT_MEASURED`) ; les libellés de seuil sont **dérivés** des constantes, donc un seuil qui bouge ne peut pas laisser un texte qui ment ; le verdict ROUGE reste celui du refus, la corrélation ne fait que l'expliquer.
- `tests/loadtest-k6/test_report_resources.py`, `test_report_conclusions.py` — ✅ 16 tests, chacun sur un comportement ; les trois branches de la corrélation sont couvertes, ainsi que les deux contre-épreuves qui comptent (palier sans cgroup → lignes **absentes** ; login lent **sans** refus → pas ROUGE).
- `tests/mss.mail.application.tests/Services/Audit/AuditBackgroundServiceFallbackTests.cs` — ✅ `JsonSerializerOptions` partagé (CA1869) ; l'aller-retour sérialise/désérialise ne peut plus diverger sur la convention de nommage.

### Suggestions (non bloquantes)

- `PGPASSWORD=postgres` apparaît une troisième fois dans `observe.ps1` (identifiant synthétique de banc, déjà présent avant cette PR). À extraire en constante si une quatrième sonde arrive — cf. la consigne S2068 de `conventions/csharp.md`, transposable.
- Les trois sondes Postgres coûtent trois `docker exec` (~200 ms chacun) par relevé au lieu d'un, soit ~4 % d'une cadence de 10 s. Fusionner la lecture cgroup dans une sonde existante gagnerait ~200 ms. **Écarté sciemment** : la séparation des sondes est une décision explicite de la US, et elle vaut plus que 4 % de cadence.

### Sécurité / données de santé

- ✅ Aucune donnée de santé dans les nouveaux échantillons, journaux et rapports. Les seuls identifiants publiés sont des noms de bases `u_9…` (RPPS **synthétiques** du banc), explicitement acceptés par la DOD.
- ✅ Aucun secret ajouté : le `PGPASSWORD=postgres` est l'identifiant de banc déjà utilisé par les sondes existantes du même fichier.
- ✅ Le nom de base passé à `psql` vient de `pg_database`, pas d'une entrée externe, et transite comme argument positionnel (`$1`), pas par interpolation dans la commande.

## Merged
- **Date** : 2026-09-11
- `api-mail` : PR #228 squash-mergée → `58556045e9163f56f553ae4cba86d2ad3ed0cde7` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/commit/58556045e9163f56f553ae4cba86d2ad3ed0cde7
- `dtos-mss` : aucune PR (branche vide, 0 commit) — ref distante `feat/task-295-bench-postgres-login-probe` supprimée, clone local repassé sur `develop`
- **CI develop api-mail** : ✓ success — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/34592853180
- **Staging** : `forge/staging-task-295-297-20260911` **conservée** — task-296 (`todo`) et task-297 (`done`, PR #229 en attente) encore actives dans ce run
- **Contexte** : mergée en préalable à task-296 (A/B mémoire Postgres) — même SHA de code sur les deux jambes, lecture avant/après sur les séries `login`, `backends/started_last_60s`, `failcnt`
