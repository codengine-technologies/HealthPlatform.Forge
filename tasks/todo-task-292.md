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
- [ ] Mesure au banc consignée dans le task file : re-tir 1000 iso
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
