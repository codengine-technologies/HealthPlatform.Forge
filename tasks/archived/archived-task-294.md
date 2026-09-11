# todo-task-294.md — À 1000 médecins, le multiplexeur PostgreSQL rejette au lieu de faire attendre : régler et mesurer PgBouncer avant de citer une latence

**Repos**: api-mail
**Dependencies**: —
**Epic**: E015
**Single frontend**: true
**Priorité**: **2** — sans ce réglage, **aucune** latence mesurée à 1000
médecins n'est opposable (5,21 % de requêtes rejetées, dont 4 090 envois),
et le palier 1000 reste non instruit. Le réglage vit dans le profil de banc
(`src/AppHost/pgbouncer/pgbouncer.ini`) ; son portage vers `DevOps/` est un
acte humain, hors forge.

> **Origine** : campagne de charge du 2026-09-08, tir 1000 médecins
> (`Docs/audits/api-mail-loadtest-campagne-post-lot-20260908.md`, finding
> **F-08P01-1** ; détail `api-mail-loadtest-journey-1000-post-lot-20260908.md`).
> Cause **mesurée** ; le levier applicatif de fond (coût Postgres de la page
> d'en-têtes hydratée et de la recherche) reste au backlog E015 et n'est pas
> l'objet de cette US.

## Objective

Que, sous saturation Postgres, le pooler fasse **attendre** les demandes du
médecin (file `cl_waiting`, latence dégradée mais service rendu) au lieu de les
**rejeter** en masse par erreur cachée — et que ce comportement soit **mesuré**
au banc, à protocole égal, avant tout portage.

### Ce qui a été mesuré (tir 1000, 12 630 s, code `develop` `9bd8a72`)

| Grandeur | 26/08 (référence) | 08/09 |
|---|---|---|
| Erreurs HTTP | 0,058 % | **5,21 %** (66 643 × 500) |
| `PostgresException` (compteur runtime) | — | **2 178 414** (1 561 018 dans les 38 min de régime) |
| Refus PgBouncer `server login has been failing, cached error: connect timeout (server_login_retry)` | 0 | **85 787**, jusqu'à 7 798 par 5 min |
| Backends en cours de login (`sv_login`) en régime | — | **212 à 243** simultanés |
| `cl_waiting` praticien | 45 % des relevés, pointe 109, `maxwait` 63 s | 100 % des relevés, pointe 135, `maxwait` 120 s |
| Postgres CPU | 15 cœurs en pointe | 11,1 moy / 15,5 pointe ; 50 backends en CPU + 31 en lecture disque |
| Cascade mesurée | — | rejeux EF Core (49 742 `NpgsqlException` + 138 873 `InvalidOperationException` transitoires) : `GetMail` « le reste » 26 → **1 932 ms**, envoi p95 14 → **38 s** ; audit : 1 477 traces perdues (`todo-task-292.md`) |

**Mécanique établie.** Un pool par base praticien (1000 pools),
`max_db_connections = 3`, `min_pool_size = 0`, **`server_idle_timeout = 60`** :
un backend inutilisé une minute est fermé, et doit être **rouvert** au geste
suivant du médecin. Sous saturation Postgres, l'ouverture d'un backend dépasse
`server_connect_timeout` (15 s par défaut) ; PgBouncer **met l'échec en cache**
(`server_login_retry`, 15 s par défaut) et répond `08P01` **en ~10 ms** à tout
client du pool, sans attendre. Le trafic est délesté (~12 % en régime), ce qui
flatte les latences des requêtes servies : les gains lus sur ce tir sont des
**bornes optimistes**. Contrôles faits : résolution IPv4 seule (`getent` →
`172.24.0.2`, le piège de `task-257` n'est pas revenu), 0 refus pendant les
2 h 15 premières, aucune charge étrangère significative sur l'hôte.

Le 26/08, à saturation comparable, le pooler **faisait attendre** (45 % de
relevés `cl_waiting`) et rendait 0,06 % d'erreurs. Ce qui a changé n'est pas la
saturation, c'est sa **forme** : réouverture permanente de backends sur 1000
pools + cache d'échec de login. Le médecin subit un **500** au lieu d'une
attente.

### Contenu attendu

1. **Réglage du pooler dans le profil de banc**, à mesurer un paramètre à la
   fois (A/B à protocole égal, base gardée) :
   - `server_idle_timeout` ≫ 60 s (ou `min_pool_size ≥ 1`) : supprimer la
     réouverture permanente — les connexions retenues suivent la population
     (1000 × 1 à 3), ce que `DevOps/DIMENSIONNEMENT-POSTGRESQL-API-MAIL.md`
     dimensionne déjà (`max_connections = 2500`) ;
   - `server_login_retry` court et/ou `server_connect_timeout` plus long :
     ne pas mettre en cache 15 s d'échec pour un login lent ;
   - `query_wait_timeout` explicite : borner l'attente en file plutôt que
     rejeter en cache — le médecin attend au pire N secondes, avec un 503
     typé (`UnavailableException`, règle 12) et non un 500 générique.
   Les valeurs retenues sont une décision de `/develop` **sur mesure** ; la
   valeur produit est : **≤ 0,1 % d'erreurs à 1000 médecins**, `08P01` = 0.
2. **Le rejet du pooler devient une erreur typée.** `08P01
   server_login_retry` et `query_wait_timeout` sortent en **503**
   `ProblemDetails` (indisponibilité temporaire, à réessayer), pas en 500
   « An unexpected error occurred » : le client peut réessayer, le médecin
   comprend. Et la stratégie de rejeu EF Core ne doit pas **amplifier** le
   rejet (139 k rejeux transitoires mesurés) : un `08P01` en cache n'est pas
   transitoire à l'échelle d'un backoff de quelques centaines de ms.
3. **Le rapport du banc lit le refus.** `report.py` publie le nombre de refus
   `server_login_retry` (journal PgBouncer) et `sv_login` dans « Coûts
   résidents », et classe le tir **ROUGE** dès qu'il est non nul — comme il le
   fait déjà pour `cl_waiting`. Le 08/09, le rapport a dû être complété à la
   main sur ce point.
4. **Re-tir 1000 iso** avec le réglage retenu, protocole du tir 1000 r2 du
   08/09 (bases gardées, `UID_BASE=365`, chauffe complète attendue puisque la
   base est désormais hydratée), et **relecture** des étapes 1 à 11 sans
   délestage : c'est ce tir qui rendra opposables les gains de `task-194` et du
   lot à 1000.

### Hors périmètre (explicite)

- **La saturation elle-même** (11–15 cœurs Postgres) : coût de la page
  d'en-têtes hydratée (`References LIKE`, `task-273`), recherche sémantique,
  charge d'écriture du journal d'audit (`todo-task-292.md`). Cette US change la
  **réponse** du système à la saturation, pas sa cause.
- Le portage de la configuration vers `DevOps/` (repo hors automation) —
  acte humain après lecture de la mesure.

## Definition of Done

- [ ] Build passes on api-mail (0 errors)
- [ ] Tests pass (0 failures)
- [ ] `src/AppHost/pgbouncer/pgbouncer.ini` : valeurs retenues **justifiées en
      commentaire par la mesure** (référence au rapport A/B), et les tests
      existants de la configuration de banc (`BenchUpstream_DoesNotRelyOnHostDockerInternal`,
      `PgBouncerTransactionPoolingTests`) toujours verts
- [ ] Test : `08P01 server_login_retry` et `query_wait_timeout` (PostgresException
      `08P01` / `57014`-`08006` selon le cas) sont mappés en **503**
      `application/problem+json` par le `GlobalExceptionHandler` (règle 12), sans
      fuite du message brut du pooler
- [ ] Test : la stratégie d'exécution EF Core ne rejoue **pas** un `08P01`
      en cache (ou le rejoue au plus une fois, sans backoff exponentiel)
- [ ] `report.py` : « Coûts résidents » porte les refus `server_login_retry` et
      `sv_login` max ; un refus non nul classe le tir ROUGE — tests
      `test_report_resources.py` / `test_report_conclusions.py` étendus ;
      `tests/loadtest-k6/selftest.sh` vert
- [ ] A/B consigné dans le task file : au moins deux jambes (réglage courant
      vs réglage retenu) sur le protocole 1000 r2, avec refus, `cl_waiting`,
      `maxwait`, erreurs HTTP, p50/p95 des 11 étapes
- [ ] Re-tir 1000 final : **erreurs ≤ 0,1 %, `08P01` = 0**, rapport `.md` +
      ligne `INDEX.md`, copie dans `Docs/audits/`
- [ ] Aucune donnée de santé dans les nouveaux logs/métriques (noms de bases
      `u_9…` acceptables, jamais d'INS)

## Manual Test Plan

- **Banc distant** (skill `loadtest-skill`) :
  `cd Api/Mail && MSS_LOADTEST=true MSS_ENFORCE_PSC_IDENTITY=false MSS_LOADTEST_MAIL_HOST=192.168.1.69 aspire run --project src/AppHost`,
  seed `--users 1000 --messages 0 --mail-host 192.168.1.69 --api http://127.0.0.1:5052`.
  Pré-vol : `docker logs <pgbouncer> | grep -icE 'unreachable|server_login_retry'` = 0,
  `getent ahosts postgres-pgvector` en IPv4 seule, garde scratch (`todo-task-293.md`)
  active tant qu'elle n'est pas livrée.
- **Tir** : `JOURNEY_STAGES=1000:12600s USERS=1000 MESSAGES_PER_USER=247 UID_BASE=365
  CORPUS_THREAD_SHARE=0.3 JOURNEY_P_TREATMENT=0.095 JOURNEY_P_READ_COLD=0.19`,
  `LATENCY_MS = 101 − RTT`. Bases **gardées** (ne pas purger).
- **Ce que l'humain doit voir** pendant la dernière heure :
  - `docker logs --since 5m <pgbouncer> | grep -c login_retry` → **0**
    (le 08/09 : 7 798) ;
  - `SHOW POOLS` : `sv_login` proche de 0, `cl_waiting` éventuellement non nul
    (attente, pas rejet), `maxwait` borné par `query_wait_timeout` ;
  - Prometheus : `rate(http_server_request_duration_seconds_count{http_response_status_code="500"}[5m])`
    ≈ 0 ; les 503 éventuels sont typés ;
  - k6 : `http_req_failed` ≤ 0,1 %, tir non classé ROUGE par le rapport ;
  - rapport : ligne « refus `server_login_retry` = 0 » dans « Coûts résidents ».
- **Contre-épreuve** : une requête envoyée pendant une saturation forcée
  (par exemple `query_wait_timeout` très court) reçoit un **503**
  `application/problem+json` avec `title`/`detail` génériques, pas un 500.
- **Rendre le banc** (étape 6 du skill), bases gardées.
- **Données de test** : synthétiques uniquement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — capacité et robustesse d'infrastructure du
  service MSSanté (EPIC E015)
- **Exigences DSR honorées** : non applicable — aucune exigence DSR ne porte sur
  le pooler ; la US sert la disponibilité du service au médecin
- **INS** : non applicable — aucune donnée patient manipulée
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : les 503 d'indisponibilité sont journalisés côté serveur
  avec `traceId` (règle 12), sans donnée de santé ; pas d'évènement métier
  nouveau
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — la configuration du pooler de banc préfigure celle
  de Staging/Production (portage humain via `DevOps/`) ; aucun nouveau flux
- **AIPD / impact RGPD** : inchangée

## Branches
- `api-mail` (pushed) : feat/task-294-pgbouncer-wait-not-reject — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-294-pgbouncer-wait-not-reject
- `dtos-mss` (pushed, auto-included) : feat/task-294-pgbouncer-wait-not-reject — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-294-pgbouncer-wait-not-reject

## Timings

*(généré par `tools/timing/report.sh --task task-294 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 7.3 s | — | — | — | — |
| /develop | ok | 15 min 47 s | 4 (13 s) | 4 (2 min 16 s) | — | api-mail 4B/4T |
| /sonar | ok | 4 min 18 s | 1 (10 s) | 5 (2 min 52 s) | 1 (26 s) | 1 itération(s), api-mail 1B/5T |
| /lint-angular | skipped | 0.6 s | — | — | — | repo/écrans non touchés (task api-mail uniquement) |
| /lint-mobile | skipped | 0.5 s | — | — | — | repo/écrans non touchés (task api-mail uniquement) |
| /verify-visual | skipped | 0.6 s | — | — | — | repo/écrans non touchés (task api-mail uniquement) |
| /review | ok | 7 min 10 s | 5 (15 s) | 2 (1 min 45 s) | — | api-mail 5B/2T |
| **Total cycle** | | **27 min 25 s** | **10 (39 s)** | **11 (6 min 53 s)** | **1 (26 s)** | |

## Develop log

- Repos touched : api-mail (dtos-mss : branche créée, aucun commit — aucun changement de contrat)
- DTOs published : no DTO change
- Interop published : no interop change
- Commits :
  - api-mail : d97b325 feat(loadtest): le multiplexeur PostgreSQL fait attendre au lieu de rejeter, et le rejet devient une erreur typée (task-294)
  - api-mail : 6b8ae28 refactor(loadtest): simplify pass (/simplify) — task-294
- Local build / test : ✓ build 0 erreur ; 167 + 486 + 2325 + 827 unitaires verts (1 échec pré-existant d'isolation `GetFolderTodayAsync_HappyPath_TagsTheImapActivity…`, réentrance statique `ActivitySources`, cf. task-292), intégration 458 verts / 16 skips / 5 rouges pré-existants de frontière de minuit (hors périmètre) ; `selftest.sh` du harnais : node 94/94, unittest 338/338 OK.
- Décisions d'implémentation :
  - **pgbouncer.ini (profil de banc)** : `server_idle_timeout` 60 → 600 et `server_lifetime` 600 → 3600 (fin de la réouverture permanente des 1000 pools — `sv_login` 212–243 mesuré), `server_connect_timeout` 15 → 30, `server_login_retry` 15 → 1 (aucun échec de login mis 15 s en cache), `query_wait_timeout` 120 → 30 (attente bornée, puis 503 typé). Ce fichier porte la jambe « tout réglé » ; les jambes A/B intermédiaires (idle+lifetime seuls, puis connect+retry, puis wait) sont à mesurer au banc — les commentaires du fichier le disent et référencent la baseline du 08/09.
  - **Rejet typé** : `GlobalExceptionHandler.IsDatabaseUnavailable` mappe `PostgresException` `08P01` / `08006` / `57014` — trouvée n'importe où dans la chaîne d'`InnerException` (la stratégie EF Core enveloppe le driver) — en **503 `ProblemDetails`** au détail générique, sans le message brut du pooler. Décision de couche assumée : le handler référence Npgsql plutôt que d'introduire un intercepteur EF Core qui traduirait en `UnavailableException` — plus simple, couvre aussi les exceptions levées hors DbContext ; alternative consignée.
  - **Stratégie d'exécution EF Core** : le chemin de données (`UseNpgsql` sans `EnableRetryOnFailure`) ne rejoue pas — test qui le prouve (`RetriesOnFailure` faux, délégué tenté une fois, `08P01` en cause racine). Les 138 873 `InvalidOperationException` « transient » du 08/09 ne viennent donc pas d'un rejeu EF : leur site d'émission reste à localiser dans Seq (suivi, hors périmètre).
  - **Harnais** : `observe.ps1` échantillonne `sv_login` et les refus `server_login_retry` par **delta** (`docker logs --since` le relevé précédent) ; `report.py` publie `sv_login` (moy/max) et le **total de refus du palier** dans « Coûts résidents », et tout refus non nul classe le tir **ROUGE** (le 08/09 le rapport avait été complété à la main).
- Passe qualité (/simplify) :
  - Applied & committed : api-mail : 10 files (6b8ae28) — mesure des refus par delta + somme sur la fenêtre (au lieu d'un cumul lu en max, qui faisait hériter les paliers et coûtait O(journal) par relevé), pattern match sans allocation sur les SQLSTATE, `GetBaseException` dans le test, consts `PostgresErrorCodes` dans les `InlineData`, classes Python avant le garde `__main__`, test doublon retiré, commentaire ini aligné sur le code.
  - Skipped (noted) : intercepteur EF Core → `UnavailableException` (couche ; alternative documentée) ; forge de `PostgresException` partagée dans `mss.mail.testing.shared` (deux factories de 3 lignes) ; fusion de la ligne « refus » dans la boucle `PGBOUNCER_WAIT_ROWS` (sémantique somme ≠ max) ; raccourcissement du récit de mesure dans l'ini (le DOD exige la justification par la mesure en commentaire).
  - Skipped (contract/excluded) : dtos-mss
- DOD self-check : 5/8 items vérifiables satisfaits (build, tests, ini avec valeurs justifiées + tests `BenchUpstream_ResolvesToIpv4WithoutHostAlias` / `PgBouncerTransactionPoolingTests` verts, mapping 503 testé sans fuite, non-rejeu EF testé, `report.py` + `selftest.sh` verts, aucune donnée de santé dans les nouveaux logs/métriques). **3 items de banc différés (HAG)** : A/B au moins deux jambes sur le protocole 1000 r2, re-tir 1000 final (erreurs ≤ 0,1 %, `08P01` = 0, rapport + `INDEX.md` + copie `Docs/audits/`), et la réécriture des commentaires ini « par la mesure » qui en découle — 3 h 30 par tir sur le banc distant.
- Next step : /sonar task-294

## Sonar log
- Phase 1 (new code) : ✓ Quality Gate OK, **0 finding new-code dès la première analyse**, new_coverage = 88,0 % (seuil QG 80 %) — `GlobalExceptionHandler.cs` : 100 % du new code couvert
- Phase 1 — Issues fixées : 0 ; Tests ajoutés : 0 (couverture déjà complète) ; Hotspots new-code : 0
- Phase 2 (legacy) : itérations 0 / 5 — skippée : baseline déjà aux cibles dures (0 bug, 0 vuln, A/A/A), 59 smells legacy hors périmètre
- Itérations d'analyse : 1
- Build / tests : ✓ green (5 échecs pré-existants de frontière de minuit, cf. Develop log — hors périmètre)

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 88,1 % | 88,0 % | −0,1 pt |
| New-code issues | 0 | 0 | → |
| Bugs | 0 | 0 | → |
| Vulnerabilities | 0 | 0 | → |
| Security hotspots | 3 (legacy) | 3 | → |
| Code smells | 59 | 59 | → |
| Coverage (projet) | 88,1 % | 88,1 % | → |
| Duplication | 0,4 % | 0,4 % | → |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

## Lint log
- /lint-angular : ⤍ skipped — `client-angular` non listé dans **Repos** (les 2 `environment.ts` modifiés dans `Client/Angular` préexistent au run, branche humaine `feature/nova-rewriting-mss`).

## Lint mobile log
- /lint-mobile : ⤍ skipped — `client-mobile` non listé dans **Repos**, `Client/Mobile` sur `develop`, arbre propre.

## Visual verify log
- /verify-visual : ⤍ skipped — aucun écran `client-mobile` touché.

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/227 — label `awaiting-human-merge`
- `dtos-mss` : aucun commit sur `feat/task-294-pgbouncer-wait-not-reject` (pas de changement de contrat) — pas de PR

## Code Review Summary
- Itération 1 : **CHANGES REQUESTED** (relecture indépendante) — 1 bloquant : `query_wait_timeout = 30` à égalité avec le `Command Timeout` Npgsql par défaut (30 s, non surchargé par `AppHost.cs`) → `TimeoutException` sans `PostgresException`, le 503 promis redevenait un 500. Suggestions : sémantique de `server_login_retry` (fenêtre de refus, pas attente), borne 1000 × 3 > `max_connections` 2500 → `53300`, garde `__main__` en double, `docker logs` en échec lu comme 0.
- Correctifs (`06cc225`) : `query_wait_timeout` = 20 + test d'invariant `QueryWaitTimeout_StaysBelowNpgsqlCommandTimeout` ; `53300` mappé en 503 (+ InlineData) ; commentaires ini alignés ; `observe.ps1` : `--since` en `ToString('o')`, aucun échantillon si `docker logs` échoue ; test Python déplacé avant le garde.
- Itération 2 : **APPROVED** — build 0 erreur, 3 806 tests unitaires verts, 458 tests d'intégration verts (5 flakes pré-existants de frontière de minuit, hors périmètre), `selftest.sh` vert, Sonar QG OK, 0 finding new-code, `GlobalExceptionHandler` couvert à 100 %.
- Suggestions restantes (hors périmètre, à suivre) : `NpgsqlException.IsTransient` / `SocketException` (pooler injoignable) en 503 ; localiser dans Seq le site émetteur des 138 873 `InvalidOperationException` « transient » du 08/09 (ce n'est pas un rejeu EF Core, prouvé) ; intercepteur EF Core → `UnavailableException` si l'on veut sortir Npgsql de la couche API.

## Merged
- **Date** : 2026-09-11
- `api-mail` : PR #227 squash-mergée → `d04f2ca4691dcf0ebf7134da506ce67e4d69d938` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/commit/d04f2ca4691dcf0ebf7134da506ce67e4d69d938 ; branche distante `feat/task-294-pgbouncer-wait-not-reject` supprimée (locale conservée)
- `dtos-mss` : aucune PR (branche vide, 0 commit) — ref distante `feat/task-294-pgbouncer-wait-not-reject` supprimée, clone local repassé sur `develop`
- **CI develop api-mail** : ✓ success — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/34569293335
- **Staging** : `forge/staging-task-292-294-20260908` supprimée (remote + local, api-mail) — run 292-294 entièrement mergé
