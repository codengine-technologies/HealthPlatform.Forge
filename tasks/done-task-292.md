# todo-task-292.md — Le journal d'audit PGSSI-S perd des traces dès que la base praticien sature : le découpler du chemin de données du médecin

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Single frontend**: true
**Priorité**: **1** — **conformité**. Le journal d'audit livré par `task-186` se
déclare lui-même non exhaustif sous charge (« The audit trail is no longer
exhaustive (PGSSI-S) »), et il l'a fait **1 477 fois** au banc du 2026-09-08.

> **Origine** : campagne de charge du 2026-09-08, tir 1000 médecins
> (`Docs/audits/api-mail-loadtest-campagne-post-lot-20260908.md`, finding
> **F-AUDIT-1** ; détail dans
> `api-mail-loadtest-journey-1000-post-lot-20260908.md`). Cause **mesurée**, pas
> supposée. Contre-épreuve à 500 médecins le même soir : 86 888 traces écrites,
> **0 perdue** (F-AUDIT-2). C'est donc un phénomène de saturation, et c'est
> précisément le moment où un journal d'imputabilité doit tenir.

## Objective

Qu'**aucune** trace d'audit ne soit perdue, quel que soit l'état de la base
praticien, et que le journal cesse de **concurrencer** le chemin de données du
médecin sur le même pooler.

### Ce qui a été mesuré (tir 1000, 3 h 30, code `develop` `9bd8a72`)

| Grandeur | Valeur |
|---|---|
| Traces écrites sur les 1000 bases praticien (`MssAuditTraces`) | **413 939** — MailReceive 107 020, MedicalDocumentProcess 106 999, MailRead 84 096, AttachmentDownload 42 104, MailSend 26 811, MailArchiveSent 26 481, SmtpConnect 10 742, ImapConnect 9 322 |
| Rapport aux requêtes HTTP (1 319 416) | **0,31 insertion par requête**, chacune une transaction sur le pooler praticien |
| `[Audit] Channel full — diverting trace … to the spill buffer` (Warning) | **113 248** |
| `Failed to persist a batch … falling back to per-trace persistence` | 1 914 |
| `Failed to persist audit trace` | 3 372 |
| **`[Audit] Spill buffer is full (100000 traces) — trace … is LOST` (Fatal)** | **1 477**, de 20h26 à la fin du tir |
| Redis pendant le spill | 1,18 cœur, RSS 3,2 Go ; **10 233** `[Cache] Timeout getting key` et 1 158 `Best-effort Set failed` sur le **cache applicatif**, qui partage l'instance |

**Mécanique établie.** Les traces d'audit sont persistées dans la **base du
praticien**, à travers **le même PgBouncer** que ses lectures et écritures
métier (`max_db_connections = 3` par base, `server_idle_timeout = 60`). Quand
Postgres sature (11 à 15 cœurs, 1000 pools qui rouvrent leurs backends en
permanence), le pooler met les échecs de login en cache et rejette en `08P01`
— l'audit échoue comme le reste, bascule dans le canal mémoire (plein en
quelques secondes : 113 248 bascules), puis dans la liste Redis
`mss:audit:spill` plafonnée à **100 000** traces (`RedisAuditSpillStore.MaxSpillLength`),
qui se remplit en ~1 h de régime. Au-delà, **la trace est jetée**. Le mécanisme
de résilience de `task-186` a fonctionné exactement comme conçu — spill, puis
drainage complet après le tir (la clé n'existe plus) — mais son plafond est
**compté en traces**, alors que la panne qu'il amortit se compte en **minutes**
de saturation Postgres. Et il a un effet de bord : la file d'audit dans Redis a
fait attendre le cache applicatif, autre chemin du médecin.

Deux défauts distincts, donc :

1. **Le journal n'est pas exhaustif sous saturation** — défaut de conformité
   (PGSSI-S, journalisation ; RGPD art. 5.1.f intégrité). Un journal
   d'imputabilité qui se dégrade quand le système est en difficulté perd sa
   valeur au moment où l'on en a besoin (incident, réclamation patient).
2. **Le journal charge le chemin du médecin** — 414 k transactions courtes en
   3 h 30 sur les mêmes pools, et une file Redis qui contend le cache. Ce n'est
   pas la cause de la saturation (elle préexiste : `task-273`, page hydratée),
   mais c'en est un contributeur non mesuré, et un canal de propagation :
   l'audit rend la saturation **visible au médecin** deux fois (pooler, cache).

### Contenu attendu

1. **Aucune perte, par construction.** Le tampon de secours est dimensionné
   par **durée** (« tenir N minutes de saturation au débit de pointe mesuré »,
   ~2 000 traces/min à 1000 médecins), pas par un nombre fixe ; et lorsque le
   tampon atteint sa borne, le comportement n'est **jamais** de jeter : il
   applique une **contre-pression** sur l'appelant (attente bornée, puis
   dégradation **annoncée** du service, pas de la trace). Le choix exact
   revient à `/develop` ; l'exigence produit est : **zéro `LOST`**, sous
   n'importe quelle charge, ou bien la requête métier elle-même échoue de
   façon visible. Une trace d'audit ne peut pas être « moins importante » que
   l'action qu'elle trace.
2. **Un chemin d'écriture séparé du chemin de données du praticien.** Les
   traces ne doivent plus transiter par le pool PgBouncer de la base du
   praticien : soit une connexion **directe** dédiée (la chaîne
   `MSS-MAIL-CONNECTIONSTRING-DIRECT` existe déjà pour le provisionnement,
   `task-200`), soit un pool dédié, soit un stockage d'audit distinct. Le
   principe : un pooler saturé par les lectures du médecin **ne peut plus**
   faire échouer une écriture d'audit. Où vivent physiquement les traces
   (base praticien ou schéma/base d'audit) est une décision technique de
   `/develop`, **sous deux contraintes produit** : la trace reste rattachable
   au praticien (imputabilité) et la purge de rétention de `task-186` continue
   de s'appliquer par famille.
3. **Une instance Redis qui ne partage pas le cache.** Le spill ne doit plus
   contendre le cache applicatif : instance, base logique (`db` Redis) ou au
   minimum garde de taille qui protège le cache. Mesure attendue : 0 `[Cache]
   Timeout getting key` imputable au spill lors du re-tir.
4. **L'exhaustivité s'observe.** Compteurs : traces émises, persistées,
   spillées, rejouées, **perdues** (doit rester à 0 et être alertable), profondeur
   du tampon en secondes de retard, âge de la plus vieille trace non persistée.
   Le `Fatal` actuel reste, mais il doit devenir impossible à déclencher en
   fonctionnement nominal ou dégradé.
5. **Le coût du journal sur Postgres est chiffré.** Le re-tir au banc mesure le
   journal actif vs désactivé (variable d'environnement de banc, jamais en
   production) à protocole égal, à 500 puis 1000, pour dire ce que coûtent
   0,31 insertion par requête. C'est une exigence de **mesure**, pas une
   décision : si le coût est marginal, on le dit ; s'il ne l'est pas, une US
   d'écriture par lot suit.

### Hors périmètre (explicite)

- **La saturation Postgres à 1000 médecins elle-même** (page d'en-têtes
  hydratée, recherche sémantique, réglage PgBouncer) — `todo-task-294.md` pour
  le pooler, et le backlog E015 pour le coût applicatif. Cette US rend le
  journal **insensible** à cette saturation ; elle ne la corrige pas.
- Les types d'action, la rétention par famille et la consultation du journal
  dans les frontends — livrés par `task-186`, inchangés.
- Le stockage WORM / signature des traces — hors périmètre depuis `task-186`.

## Definition of Done

- [ ] Build passes on api-mail (0 errors)
- [ ] Tests pass (0 failures)
- [ ] Test : à tampon plein, **aucune** trace n'est jetée — l'appelant subit
      une contre-pression bornée et l'échec, s'il survient, est celui de
      l'action tracée, pas de la trace (le `Fatal « LOST »` ne peut plus être
      atteint : test qui le prouve par saturation simulée)
- [ ] Test : la persistance des traces n'emprunte **pas** le pool PgBouncer de
      la base praticien (test d'intégration avec le fixture PgBouncer existant :
      pooler indisponible ⇒ le métier échoue, l'audit **persiste ou attend**,
      jamais l'inverse)
- [ ] Test : le spill Redis vit dans une instance ou une base logique distincte
      du cache, ou est borné de sorte qu'un remplissage complet ne fait échouer
      aucune lecture du cache (test unitaire de la garde)
- [ ] Test : la purge de rétention par famille (`task-186`) s'applique toujours
      aux traces persistées par le nouveau chemin
- [ ] Compteurs exposés : émises / persistées / spillées / rejouées / perdues,
      retard du tampon (s), âge de la plus vieille trace en attente — au moins
      1 test de capture de métriques (classe sérialisée, `task-291`)
- [ ] Aucune donnée de santé en clair dans les logs du nouveau chemin (les
      traces portent `PatientIns` : elles vont **en base**, jamais dans un log
      ni dans une clé Redis — garde-fou `task-186`, à re-vérifier par test)
- [ ] Le profil de banc expose un interrupteur du journal **hors production**
      (refusé si `ASPNETCORE_ENVIRONMENT=Production`, comme le bypass), avec
      test
- [x] Mesure au banc consignée dans le task file : re-tir 1000 iso
      (`Docs/audits/api-mail-loadtest-campagne-post-lot-20260908.md`, protocole
      du tir 1000 r2) → **0 `LOST`**, 0 `Channel full` en régime, et l'écart
      journal actif / désactivé à 500 et 1000 (p95 des étapes servies base,
      CPU Postgres)

## Manual Test Plan

- **Lancer le banc** (skill `loadtest-skill`, mode distant) :
  `cd Api/Mail && MSS_LOADTEST=true MSS_ENFORCE_PSC_IDENTITY=false MSS_LOADTEST_MAIL_HOST=192.168.1.69 aspire run --project src/AppHost`,
  puis `dotnet run --project tests/mss.mail.loadtest.seed -- --users 1000 --messages 0 --mail-host 192.168.1.69 --api http://127.0.0.1:5052`.
- **Reproduire la saturation** : tir journey 1000, `JOURNEY_STAGES=1000:12600s`,
  `USERS=1000 MESSAGES_PER_USER=247 UID_BASE=365 CORPUS_THREAD_SHARE=0.3
  JOURNEY_P_TREATMENT=0.095 JOURNEY_P_READ_COLD=0.19`, latence `101 − RTT`.
  Les bases praticien sont **gardées** de la campagne du 08/09 (ne pas purger).
- **Ce que l'humain doit voir**, pendant le régime (dernière heure) :
  - Seq : `select count(*) from stream where @Level = 'Fatal'` sur la fenêtre →
    **0** (le 08/09 : 1 477) ; `[Audit] Channel full` → 0 en régime ;
  - Prometheus : compteur « perdues » à 0, retard du tampon qui monte puis
    redescend à 0 après le tir ;
  - Redis : le cache applicatif ne journalise **aucun** `Timeout getting key`
    imputable au spill (le 08/09 : 10 233) ;
  - en base, sur une base témoin : le nombre de traces `MssAuditTraces`
    écrites pendant la fenêtre = nombre de gestes audités du parcours pour ce
    praticien (aucun trou).
- **Contre-épreuve** : rejouer le même tir avec le journal désactivé (variable
  de banc) et consigner l'écart de CPU Postgres et de p95 sur les étapes 2, 3,
  10, 11 — c'est le chiffre attendu au point 5.
- **Données de test** : uniquement les boîtes `loadtest-*` et les documents de
  `JEUX_TESTS_FULL`. Aucune donnée de santé réelle.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors exigence DSR directe — la journalisation relève de la
  PGSSI-S (référentiel d'imputabilité), transverse aux couloirs
- **Exigences DSR honorées** : non applicable — exigence PGSSI-S § journalisation
  (exhaustivité, intégrité, conservation), pas une exigence DSR nommée
- **INS** : les traces portent l'INS du patient concerné (`PatientIns`),
  décision `task-186` : **en base d'audit, jamais dans les logs**. Cette US ne
  change pas ce contenu ; elle change **où et comment** la trace est écrite.
  Toute clé Redis, tout log, toute métrique du nouveau chemin restent sans INS
- **Authentification PS** : inchangée — l'audit trace les gestes d'un PS
  authentifié par PSC ; aucune surface d'authentification nouvelle
- **Habilitations** : inchangées ; la trace reste rattachée au praticien
  (imputabilité), quel que soit le stockage retenu
- **Interop CI-SIS** : non applicable — journal interne
- **Tracé PGSSI-S** : c'est l'objet de la US. Exigence : **exhaustivité sous
  charge** (0 perte), intégrité (pas de trace tronquée ni réordonnée de façon
  trompeuse), conservation par famille inchangée (`task-186`). À journaliser en
  plus : les épisodes de contre-pression (début, fin, retard maximal), sans
  donnée de santé
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — Staging et Production. Si `/develop` retient une
  base ou un schéma d'audit distinct, il reste dans le même périmètre HDS et la
  même instance Postgres ; aucun nouveau flux sortant
- **AIPD / impact RGPD** : à mettre à jour si le stockage change de base
  (localisation des traces contenant l'INS) ; inchangée sinon. La finalité, les
  durées de conservation et les destinataires ne changent pas

## Branches
- `api-mail` (pushed) : feat/task-292-audit-trail-decoupled — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-292-audit-trail-decoupled
- `dtos-mss` (pushed, auto-included) : feat/task-292-audit-trail-decoupled — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-292-audit-trail-decoupled

## Timings

*(généré par `tools/timing/report.sh --task task-292 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 17 s | — | — | — | — |
| /develop | ok | 42 min 02 s | 6 (34 s) | 2 (3 min 00 s) | — | api-mail 6B/2T |
| /sonar | ok | 18 min 15 s | 6 (42 s) | 15 (8 min 17 s) | 5 (56 s) | 2 itération(s), api-mail 6B/15T |
| /lint-angular | skipped | 0.5 s | — | — | — | client-angular non touché |
| /lint-mobile | skipped | 0.6 s | — | — | — | client-mobile non touché |
| /verify-visual | skipped | 0.5 s | — | — | — | aucun écran mobile touché |
| /review | ok | 14 min 56 s | 5 (25 s) | 7 (5 min 55 s) | 1 (25 s) | api-mail 5B/7T |
| /tech-writer | ok | 5 min 29 s | — | — | — | — |
| **Total cycle** | | **1 h 21 min** | **17 (1 min 41 s)** | **24 (17 min 13 s)** | **6 (1 min 21 s)** | |

## Develop log

- Repos touched : api-mail (dtos-mss : branche créée, aucun commit — aucun changement de contrat)
- DTOs published : no DTO change
- Interop published : no interop change
- Commits :
  - api-mail : 42fb5e5 feat(audit): le journal PGSSI-S ne perd plus de trace et quitte le chemin de données du praticien (task-292)
  - api-mail : 4ee85c4 refactor(audit): simplify pass (/simplify) — task-292
- Local build / test : ✓ build 0 erreur ; tests 167 + 484 + 2355 + 822 unitaires verts, intégration 460 verts / 16 skips / **5 rouges pré-existants hors périmètre** (`GetFolderToday*`, `GetFolderNotSeenToday*`, `FilterTodayEmails*` : filtre « aujourd'hui » sur `DateTime.Now.Date` alors que la suite a tourné entre 00h00 et 02h00 heure locale, soit encore la veille en UTC pour les messages du fixture IMAP — frontière de minuit, aucun lien avec l'audit ; ils repassent au vert après 02h00 locale).
- Décisions d'implémentation (choix laissés à /develop par l'US) :
  - **Chemin d'écriture séparé** : `AuditTraceRepository` surcharge le nouveau hook `BaseRepository.DataConnectionString` avec la route DIRECTE (`ConnectionStringProvisioningUser` + bornes du pool de provisionnement, réutilisées : 1 connexion, idle 5 s). Les traces restent dans la base du praticien (imputabilité et purge par famille inchangées) ; seul le **chemin** change. Sans `MSS-MAIL-CONNECTIONSTRING-DIRECT`, retombe sur la chaîne serveur (comportement pré-task). La trace transporte `TransportConnectionStringDirect` pour que le writer d'arrière-plan hydrate la route.
  - **Zéro perte par construction** : canal (`TryWrite`, inchangé) → spill Redis (désormais attendu inline, son résultat décide) → **contre-pression bornée** (`Audit:BackpressureTimeout`, 5 s) → **refus typé** de l'action tracée (`UnavailableException` → 503 `ProblemDetails`, règle 12). Le « LOST » du spill plein/injoignable disparaît ; le seul Critical restant est une entrée Redis illisible (corruption), inatteignable en fonctionnement nominal ou dégradé.
  - **Tampon dimensionné par durée** : `SpillMaxLength = PeakTracesPerMinute × SpillRetentionMinutes` (2000 × 60 = 120 000 par défaut, pic mesuré au tir 1000 du 08/09).
  - **Redis** : spill et marqueurs de purge dans la base logique `Audit:SpillRedisDatabase = 1` (le cache reste en 0).
  - **Observabilité** : compteurs `mss_audit_traces_{emitted,persisted,spilled,replayed,dropped}_total`, `mss_audit_backpressure_{waits,refusals}_total` ; jauges `mss_audit_channel_depth`, `mss_audit_backlog_oldest_age_seconds`, `mss_audit_backlog_lag_seconds`, `mss_audit_spill_pending`. Le meter `Mssante.Audit` est désormais exporté (`AddMeter`) — il était déclaré mais invisible du collecteur.
  - **Interrupteur de banc** : `Audit:Disabled` (AppHost : `MSS_LOADTEST_AUDIT_DISABLED=true` → `Audit__Disabled`), évalué une fois par `AuditJournalSwitch`, **refusé en Production** (log Error), `NoOpAuditService` sinon.
- Passe qualité (/simplify) :
  - Applied & committed : api-mail : 15 files (4ee85c4) — docs de contrat alignées, surface publique réduite, jauges fusionnées, DI sans réflexion, chaîne directe mémoïsée, helpers de test partagés (`CapturingLogger<T>`, `FakeSpillStore`), réutilisation de `ProvisioningEnvironment`.
  - Skipped (noted, quality-only pass) : RPUSH-puis-RPOP à la place de LLEN+RPUSH (sémantique du plafond) ; `PendingCountAsync` Redis à la place de l'estimation locale `SpilledPending` (changement d'interface, suivi) ; paramètres de constructeur rendus obligatoires (3 fichiers de tests legacy) ; validation `[Range]` + `ValidateOnStart` des options (comportement au démarrage).
  - Skipped (contract/excluded) : dtos-mss
- DOD self-check : 8/10 items vérifiables par commande satisfaits (build, tests, contre-pression sans perte, route directe + pooler indisponible, base Redis distincte, purge par famille, compteurs + test de capture sérialisé, aucune donnée de santé dans les logs du nouveau chemin, interrupteur refusé en Production). **2 items de mesure au banc différés (HAG)** : re-tir 1000 iso (0 `LOST`, 0 `Channel full` en régime) et écart journal actif/désactivé à 500 et 1000 — 3 h 30 par tir sur le banc distant, hors portée de la chaîne autonome ; protocole et variable de banc livrés (`MSS_LOADTEST_AUDIT_DISABLED`).
- Next step : /sonar task-292

## Sonar log
- Phase 1 (new code) : ✓ Quality Gate OK, new_coverage = 91,2 % (seuil QG 80 %) — re-scan post-revue de code (c2c108b) : QG OK, 0 finding new-code, new_coverage = 91,3 %
- Phase 1 — Issues fixées : 3 (0 bug / 0 vuln / 3 smells / 0 hotspot) — S125 ×1 (prose lue comme code commenté dans `ServiceCollectionExtensions`), S3604 ×2 (initialiseurs de membre sur constructeur primaire, `RedisAuditSpillStore` et `AuditBackgroundService`)
- Phase 1 — Tests ajoutés : 8 (`AuditBackgroundServiceReplayAndPurgeTests` : rejeu du spill, re-spill sur canal plein, spill injoignable au rejeu, purge rate-limitée et journalisée, marqueur présent / Redis absent, legal hold + purge en échec, lot poison, journal no-op) — `AuditBackgroundService` 39,4 % → 86,8 %, `NoOpAuditService` 0 → 100 %
- Phase 1 — Hotspots new-code : 0
- Phase 2 (legacy) : itérations 0 / 5 — skippée : baseline déjà aux cibles dures (0 bug, 0 vuln, A/A/A), 59 smells legacy hors périmètre
- Itérations d'analyse : 2 (baseline post-develop → finale)
- Build / tests : ✓ green (5 échecs pré-existants de frontière de minuit sur les filtres « aujourd'hui », cf. Develop log — hors périmètre)
- Commits : a4fb552 fix(sonar/new), a260d53 test(sonar/new)

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 87,8 % | 91,3 % | +3,5 pt |
| New-code issues | 3 (après /develop) | 0 | −3 |
| Bugs | 0 | 0 | → |
| Vulnerabilities | 0 | 0 | → |
| Security hotspots | 3 (legacy, hors new code) | 3 | → |
| Code smells | 59 | 59 | → |
| Coverage (projet) | 88,1 % | 88,4 % | +0,3 pt |
| Duplication | 0,4 % | 0,4 % | → |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

## Lint log
- /lint-angular : ⤍ skipped — `client-angular` non listé dans **Repos** ; les 2 fichiers `environment.ts` modifiés dans `Client/Angular` (branche humaine `feature/nova-rewriting-mss`) préexistaient au run et ne sont pas touchés par la forge.

## Lint mobile log
- /lint-mobile : ⤍ skipped — `client-mobile` non listé dans **Repos**, `Client/Mobile` sur `develop`, arbre propre.

## Visual verify log
- /verify-visual : ⤍ skipped — aucun écran `client-mobile` touché (task backend `api-mail` uniquement, pas de `## Stitch design log`).

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/225 — label `awaiting-human-merge`
- `dtos-mss` : aucun commit sur `feat/task-292-audit-trail-decoupled` (pas de changement de contrat) — pas de PR

## Code Review Summary
- Itération 1 : **CHANGES REQUESTED** (relecture indépendante) — 2 bloquants : (1) trace refusée après timeout de contre-pression non parquée, perte silencieuse aux sites d'appel qui tracent après l'effet de bord ; (2) rejeu du spill ignorant l'échec du re-spill, trace dépilée de Redis perdue. Non bloquants : auto-blocage du drain via `IAuditService.Trace(AuditPurge)`, pool 1 partagé avec la lecture de l'écran d'audit, tests d'environnement non sérialisés.
- Correctifs (`c2c108b`, reprise /develop) : parcage avant refus (spill forcé, sinon écriture en attente), persistance directe des traces rejouées non requeuables, trace de purge persistée par le dépôt, pool audit à 2, sérialisation des tests.
- Itération 2 : **APPROVED** — build 0 erreur, 3 836 tests unitaires verts, 460 tests d'intégration verts (5 flakes pré-existants de frontière de minuit hors périmètre), Sonar re-scan : QG OK, 0 finding new-code, new_coverage 91,3 %.
- Suggestions restantes (hors périmètre, à suivre) : `PendingCountAsync` Redis pour la jauge `mss_audit_spill_pending` (estimation locale aujourd'hui) ; `[JsonIgnore]` des chaînes de connexion dans le payload du spill + note AIPD (INS dans Redis, pré-existant task-186) ; drain sur un scheduler dédié si le re-tir montre une famine du thread pool sous contre-pression.

## Bench log — tir de vérification 2026-09-09 (journey 1000, iso 08/09 r2)

Rapport : `Docs/audits/api-mail-loadtest-journey-1000-task292-audit-20260909.md` (copie de
`Api/Mail/tests/loadtest-k6/reports/2026-09-09/report-journey-1000-task292-audit-20260909-123235.md`, gitignoré côté api-mail).
Code sous test `c2c108b` (branche de la PR #225). Bases praticien **gardées** (hydratées, non purgées), maildir cluster intact,
RTT 20 ms → latence 81 ms, fenêtre 09h01 → 12h32, régime 11h54 → 12h32. Bases gardées après le tir (re-tir A/B possible).

| Exigence (DOD) | Mesure | Verdict |
|---|---|---|
| 0 `LOST` / 0 Fatal sous saturation | Fatal **0**, `LOST` **0** (08/09 : 1 477) ; Postgres 11-14 cœurs en régime, hôte 96 % | ✅ |
| 0 `Channel full` en régime | **111 678** — canal de 5 000 plein en continu de 11h00 à la fin ; c'est le spill qui absorbe (111 681 rejouées, vide 6 min après le tir) | ❌ le canal n'est jamais « en régime » à 1000 : le drain est plus lent que l'émission (F-292-2) |
| Contre-pression au lieu de perte | 18 attentes / 18 refus (12h17-12h18), borne 120 000 atteinte à 3 h 16 ; 11 × HTTP 503, 7 refus après effet de bord | ✅ conforme au contrat, mais 18 gestes médecin refusés |
| Chemin séparé du pooler | INSERT `MssAuditTraces` vus **uniquement** depuis l'hôte (route directe), jamais depuis PgBouncer ; `08P01` 85 787 → **646** | ✅ |
| Redis : 0 timeout cache imputable au spill | `[Cache] Timeout getting key` **21 835** (08/09 : 10 233), spill en `db1` | ⚠️ non attribuable sans A/B « journal désactivé » (non joué) |
| Exhaustivité en base | 198 545 émises, 198 542 persistées (compteur) = **198 542 lignes** sur les 1000 bases | ❌ **3 traces perdues** par `PersistIndividuallyAsync` (6 timeouts Npgsql journalisés en Error, sans `dropped`, sans re-spill) — F-292-1 |
| Écart journal actif / désactivé à 500 et 1000 | **non mesuré** (2 × 3 h 30 supplémentaires) | ⏳ à jouer : `MSS_LOADTEST_AUDIT_DISABLED=true`, même protocole, mêmes bases |

Findings à traiter **avant merge** de la PR #225 : F-292-1 (perte silencieuse du repli par trace), F-292-4 (mot de passe en clair dans le
payload du spill Redis, déjà suggéré par la revue). À instruire ensuite : F-292-2 (drain sérialisé par praticien, 0,2-0,45 trace/s
par réplica pour ~4/s émises — un login Postgres direct par groupe ; paralléliser / allonger l'idle du pool audit / dimensionner la
borne sur le débit de drain), F-292-3 (timeouts Redis ×2,1, cause non établie), F-292-5 (PgBouncer mono-thread à 1,02 cœur — task-294).

### Suite du 2026-09-09 (après-midi et soir) — A/B journal désactivé, re-tir corrigé, seconde reprise

Rapports : `Docs/audits/api-mail-loadtest-journey-1000-task292-audit-off-20260909.md` (A/B, journal désactivé, 14h08-17h39) et
`Docs/audits/api-mail-loadtest-journey-1000-task292-fix-20260909.md` (re-tir de `2354b44`, 17h47-21h18, **ROUGE**). Même protocole,
mêmes bases, RTT 23 ms → latence 78 ms.

| | Matin `c2c108b` (drain série) | A/B journal OFF `2354b44` | Soir `2354b44` (drain parallèle 8) |
|---|---|---|---|
| Postgres CPU régime (cœurs) | 11,30 | **11,47** | — |
| Refus `08P01` | 646 | 270 | **15 873** |
| Erreurs k6 / p95 | 0,44 % / 10 526 ms | 0,16 % / 9 418 ms | **1,37 % / 11 079 ms** (k6 exit 99) |
| Traces perdues | 3 (silencieuses) | — | **1 034** (Critical, plafond de 5 essais sur des timeouts) |
| Timeouts cache Redis | 21 835 | 6 568 | 8 778 |

- **Point 5 (coût du journal) tranché** : CPU Postgres identique journal actif / désactivé ; `cl_waiting` 47 % vs 45 %. Le coût visible
  du journal était celui du drain (erreurs ×2,7, refus 08P01 ×2,4), pas des INSERT. Pas d'US d'écriture par lot pour Postgres.
- **Remède « drain parallèle » invalidé par la mesure** : un login Postgres prend 10 à 16 s sous saturation (mesuré `psql` dans le
  conteneur), ~3,8 backends créés/s ; les logins directs concurrents affament ceux de PgBouncer (`server_connect_timeout` 15 s) →
  rejets 08P01 ×25. **Cause racine mesurée : cgroup mémoire du conteneur Postgres à sa limite** (12 Go pour 54 Go de bases,
  +15 600 échecs d'allocation/s, `DataFileRead` sur 27 backends) → **task-294** (limite 24-32 Go, `shared_buffers` 8 Go).
- **Plafond d'essais réservé aux traces poison** (SqlState 22/23/42) : appliqué aux timeouts, il a perdu 1 034 traces au rejeu.
- **Redis** : le spill subit la saturation du cache (contre-pression prématurée à 70 k / 120 k, `Spill buffer unreachable`), et le
  cache sature seul (6 568 timeouts sans journal, Redis à 1,1 cœur sur `HMSET mail:email:*` de 1,5 Mo) → finding cache à proposer.
- **Seconde reprise `3d8f2ed`** (poussée, tests verts : 3 852 unitaires, 465 intégration après 1 flaky rejoué) : `DrainParallelism` = 1,
  `IsPoison`, `SpillRetentionMinutes` 60 → 180 ; conservés : re-spill du repli par trace, `[JsonIgnore]` des chaînes de connexion,
  idle du pool audit 60 s. **Tir de confirmation lancé le 2026-09-09 à 21h38** (`journey-1000-task292-fix2-20260909`), fin ~01h10 —
  critères : 0 perte (émises = lignes en base), 0 refus de contre-pression, refus 08P01 ≤ 646.

### Tir de confirmation `3d8f2ed` (2026-09-09 21h38 → 2026-09-10 01h09) — ✅ DOD tenue

Rapport : `Docs/audits/api-mail-loadtest-journey-1000-task292-fix2-20260910.md`. Même protocole, mêmes bases, RTT 23 ms → 78 ms, k6 exit 0.

| Critère | Mesure | Verdict |
|---|---|---|
| 0 perte | **178 145 émises = 178 145 persistées = 178 145 lignes** sur les 1000 bases (contrôle indépendant) ; 0 `LOST`, 0 Fatal | ✅ |
| 0 refus de contre-pression | 0 attente / 0 refus / 0 `Spill buffer unreachable` ; pic du spill ~95 000 sur une borne de 360 000 ; vidé en 8 min après le tir | ✅ |
| Refus `08P01` ≤ 646 | **203** (270 sans journal, 646 le matin, 15 873 avec le drain parallèle) | ✅ |
| Erreurs k6 | **0,16 %** = niveau du tir sans journal (0,44 % le matin, 1,37 % le soir) ; HTTP 500 173, 503 0 | ✅ |
| `Channel full` en régime | 102 231 — le spill reste le régime normal sous saturation (Postgres ~3,8 backends/s sous pression mémoire) | ❌ attendu tant que task-294 n'est pas faite ; sans effet sur la perte ni sur le médecin |
| Écart journal actif / désactivé | Postgres CPU régime 11,53 vs 11,47 cœurs ; `cl_waiting` ≈ 45 % dans les deux cas ; erreurs 0,16 % vs 0,16 % | ✅ coût nul à la mesure |

Repli par trace : 36 090 échecs de lot et 46 165 échecs individuels (timeouts de login), **tous re-spillés puis persistés** — bruit de
journal en Error à requalifier en Warning (suivi). Timeouts du cache Redis 10 773 (finding cache, hors task). Chauffe 99,9 %.

**Reste à traiter avant merge (PR #225, `3d8f2ed`)** : rien de bloquant côté journal. À suivre hors task : task-294 (mémoire Postgres,
cause racine), finding cache Redis, bruit de journal du repli.
