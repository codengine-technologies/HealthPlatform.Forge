# todo-task-422.md — Le mur des connexions Postgres : moins de connexions retenues par médecin actif, mesuré par escalier

**Repos**: api-mail
**Dependencies**: — (aucune ; task-423 est indépendante et peut passer avant)
**Epic**: E015
**Single frontend**: true
**Priorité**: **2**. La limite mesurée, environ **1 300 médecins actifs en même temps**, est au-dessus de la
population cible : 10 000 inscrits, soit environ 850 à 950 actifs selon le modèle terrain. La marge est
d'environ 40 %. Le mur est franc : au-delà, un quart des requêtes échoue d'un coup. Il faut l'éloigner, ou à
défaut le rendre progressif.

> **Origine.** Campagne « limites » des 2026-11-04 et 2026-11-05, demandée par l'humain : IA simulée, tireur
> k6bench, banc mail du cluster, 1996 boîtes hydratées.
> - Itération 1, escalier `journey` 200 → 400 → 700 → 1000 → 1400 → 1996 médecins actifs, 18 min par palier,
>   K = 1. Rapport : `Api/Mail/tests/loadtest-k6/reports/2026-11-05/report-journey-escalier-1996-20261104-ia-simulee-013324.md`,
>   finding **F1**.
> - Référence terrain : `Api/Mail/tests/loadtest-k6/reports/2026-11-04/report-terrain-1996-20261104-ia-simulee-chauffe-froide-233108.md`.

## Ce qui est établi

| Médecins actifs | Requêtes/s | Erreurs | Backends Postgres (max) | Backends du pooler (max) | Dashboard p95 |
|---|---|---|---|---|---|
| 200 | 41 | 0 % | 437 | 407 | 507 ms |
| 400 | 82 | 0 % | 816 | 786 | 507 ms |
| 700 | 144 | 0 % | 1 399 | 1 368 | 523 ms |
| 1000 | 209 | 0 % | 1 955 | 1 924 | 525 ms |
| 1400 | 254 | **24,8 %** | **2 506** | 2 477 | 2 165 ms |
| 1996 | 351 | **40,5 %** | **2 506** | 2 475 | 2 461 ms |

- **Cause mesurée** (Seq, 2026-11-04T23:57Z, début du palier 1400) : Postgres répond
  `53300 sorry, too many clients already` (`max_connections` = 2 500), puis PgBouncer met l'échec en cache et
  répond `08P01 … server_login_retry` (1 382 refus) aux clients du pool.
- **Loi mesurée** : les backends du pooler valent environ **1,9 × le nombre de médecins actifs**, à chaque
  palier, quel que soit le débit. C'est le `default_pool_size = 2` de `Api/Mail/src/AppHost/pgbouncer/pgbouncer.ini`
  appliqué à une base par boîte active. Le plafond se calcule d'avance : (2 500 − 25 directs) ÷ 1,9 ≈ 1 300.
- **Ce n'est ni le CPU** (≤ 1,6 cœur par réplica, file ThreadPool ≤ 27), **ni l'IA** (simulée), **ni IMAP**.
- **Avant le mur, la dégradation est douce** : débit × 5 entre 200 et 1000, p95 du dashboard + 4 %.
- **La mémoire du conteneur Postgres est déjà à 100 % de son cgroup** sur tout le tir : relever
  `max_connections` seul n'est pas un levier gratuit (cf. task-296, ~50 Go nécessaires à 1000 bases).

## Objective

Que le nombre de connexions Postgres retenues par médecin actif **baisse**, sans dégrader ce que le médecin
ressent, de sorte que le mur s'éloigne au-delà de 1 300 actifs. Le choix du levier se fait **par la mesure**,
un facteur par jambe, sur le même escalier que la référence.

### Contenu attendu — un facteur par jambe, dans cet ordre

1. **Jambe A, la référence** : le rapport de l'itération 1 ci-dessus. Elle n'est pas rejouée.
2. **Jambe B, `default_pool_size` 2 → 1** (`reserve_pool_size` et `max_db_connections` inchangés). Le A/B du
   2026-07-27 l'avait écarté à 200 praticiens (p95 + 13 à + 32 %, `cl_waiting` sur la moitié des relevés). Le
   code a beaucoup changé depuis (task-322, task-323, task-419), et c'est le seul réglage qui agit directement
   sur le ratio de 1,9. Il est donc remesuré, à l'échelle où il compte.
3. **Jambe C, seulement si B est rejetée** : le levier suivant, choisi d'après ce que B a montré, consigné
   dans le task file avec sa raison avant le tir. Par exemple : `max_db_connections` 3 → 2, ou la part des
   requêtes qui ouvrent une transaction sans en avoir besoin.

Chaque jambe rejoue **le même escalier** : 6 paliers × 18 min, K = 1, IA simulée, mêmes bases, sans remise à
zéro. Elle est acceptée si :
- le mur recule : 0 erreur au palier 1400, ou backends par actif < 1,6 au palier 1000 ;
- **et** aucune étape du parcours ne se dégrade de plus de 20 % au p95 aux paliers 200 à 1000, face à la jambe A.

La valeur retenue est écrite dans `pgbouncer.ini` avec son commentaire de mesure, comme les réglages
précédents (date, tirs, chiffres, rapport). Une jambe rejetée laisse le fichier inchangé, et le task file dit
pourquoi.

### Hors périmètre

- **La configuration Postgres et PgBouncer de production** vit dans `DevOps` (géré manuellement par l'humain).
  Cette task ne change que le profil de banc de l'AppHost. Elle produit la recommandation chiffrée pour
  `DevOps/DIMENSIONNEMENT-POSTGRESQL-API-MAIL.md`, que l'humain reporte.
- **Les réponses rendues au médecin quand le mur est atteint** (500, 403) : task-423.
- **Le jugement de la chauffe dans le rapport** : task-424.

## Definition of Done

- [ ] Build passes (0 errors) : `HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) : `HealthPlatform.Api.Mail.sln`. Exception admise : les 3 tests « du jour » de
      l'intégration, rouges connus entre 00:00 et 02:00, à condition d'être rejoués verts après 02:00
- [ ] Jambe B tirée selon le protocole ci-dessus. Son rapport est rangé sous `Api/Mail/tests/loadtest-k6/reports/`
      et relié dans le task file, avec la table palier par palier : erreurs, backends Postgres, backends du pooler,
      backends par actif, p95 de chaque étape. Écart de chaque étape face à la jambe A
- [ ] Verdict de la jambe B écrit dans le task file : acceptée ou rejetée, selon les deux critères ci-dessus
- [ ] Si B est rejetée : jambe C consignée avant le tir (levier et raison), tirée, et jugée de la même façon
- [ ] `pgbouncer.ini` porte la valeur retenue et son commentaire de mesure. Si aucune jambe n'est acceptée, le
      fichier est inchangé et son commentaire mentionne les jambes rejetées, avec leurs chiffres
- [ ] Recommandation pour la production écrite dans le task file : réglage, nombre de médecins actifs visé,
      `max_connections` et mémoire Postgres correspondants, à reporter par l'humain dans `DevOps`
- [ ] Iso-conditions vérifiées et consignées pour chaque jambe : même lignée de code (`git log` de l'API),
      mêmes bases (pas de purge), même tireur, même banc mail, `LATENCY_MS` identique, IA simulée
      (« 🧪 simulée » dans le rapport)
- [ ] Aucun changement de code applicatif. Si une jambe C en exige un, il est décrit dans le task file avant
      d'être écrit, et il porte ses tests unitaires et son test d'intégration (règle 1b)
- [ ] Aucune donnée de santé en clair : le banc n'emploie que des données synthétiques, aucune donnée de santé
      réelle n'est versée dans les rapports

## Manual Test Plan

1. **Lancer le banc** (skill `loadtest-skill`) :
   `MSS_TENANT_REGISTRY_DB=mss_registry_loadtest MSS_LOADTEST_MAIL_HOST=192.168.1.69 MSS_LOADTEST_AI=fake dotnet run --project src/AppHost --launch-profile https-load-test`
   depuis `Api/Mail`.
2. **Vérifier le réglage chargé** : sur la console d'administration de PgBouncer, `SHOW CONFIG;` affiche la
   valeur de la jambe.
3. **Tirer l'escalier** depuis k6bench, avec les variables de la jambe A (rapport de référence, section
   Contexte) : `JOURNEY_STAGES="200:18m,400:18m,700:18m,1000:18m,1400:18m,1996:18m"`,
   `JOURNEY_TIME_COMPRESSION=1`, `JOURNEY_WARMUP_HYDRATED=1`.
4. **Pendant le palier 1000** : `select count(*) from pg_stat_activity` reste sous le seuil attendu de la jambe.
5. **Après le tir** : attendre `pg_stat_activity` < 2 000, puis `VERIFY_MAX_USERS=2000 tests/loadtest-k6/report.sh <json>`.
6. **Comparer** la table du genou et les coûts résidents à ceux de la jambe A.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur. Dimensionnement interne, sans exigence fonctionnelle nouvelle
- **Exigences DSR honorées** : non applicable. Disponibilité du service de messagerie, aucun comportement visible
  du PS ne change en deçà du mur
- **INS** : non applicable. Aucun trait d'identité n'est manipulé
- **Authentification PS** : inchangée (PSC / e-CPS)
- **Habilitations** : inchangées. Une base par boîte, verdict de l'opérateur inchangé (règle 14) : la task change
  le nombre de connexions vers une base, jamais qui y accède
- **Interop CI-SIS** : non applicable. Aucun échange métier ne change
- **Tracé PGSSI-S** : inchangé. La route directe du journal d'audit (task-292, task-298) n'est pas modifiée ;
  si une jambe la touchait, la non-perte de traces devrait être reprouvée
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui, environnement inchangé. Le banc n'emploie que des données synthétiques
- **AIPD / impact RGPD** : inchangé, aucun traitement nouveau

## Branches

- `api-mail` (pushed) : feat/task-422-mur-des-connexions-postgres-moins-de — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-422-mur-des-connexions-postgres-moins-de
  - Créée depuis `origin/develop` (`e31fac4d`).
