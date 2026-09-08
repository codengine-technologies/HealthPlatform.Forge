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
