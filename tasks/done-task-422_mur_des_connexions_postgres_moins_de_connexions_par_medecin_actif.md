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

## Jambe B — `default_pool_size` 2 → 1 : **acceptée**

- **Rapport** : `Api/Mail/tests/loadtest-k6/reports/2026-11-05/report-journey-escalier-1996-20261105-task422-pool1-185011.md`
  (section « Analyse — task-422, jambe B » en tête). Tir du 2026-11-05, 15:58 → 17:50 UTC, TESTID
  `journey-escalier-1996-20261105-task422-pool1`.
- **Référence (jambe A)** : `…/2026-11-05/report-journey-escalier-1996-20261104-ia-simulee-013324.md`.

### Palier par palier

| Actifs | Erreurs A → B | Backends Postgres max A → B | Backends du pooler max A → B | Backends par actif A → B |
|---|---|---|---|---|
| 200 | 0 → 0 % | 437 → 246 | 407 → 217 | 2,19 → 1,23 |
| 400 | 0 → 0 % | 816 → 441 | 786 → 410 | 2,04 → 1,10 |
| 700 | 0 → 0 % | 1 399 → 738 | 1 368 → 707 | 2,00 → 1,05 |
| 1000 | 0 → 0 % | 1 955 → **1 038** | 1 924 → 1 007 | 1,96 → **1,04** |
| 1400 | 24,8 → 7,6 % ¹ | 2 506 → 1 436 | 2 477 → 1 404 | — → 1,03 |
| 1996 | 40,5 → 40,0 % ¹ | 2 506 → 2 029 | 2 475 → 1 997 | VOID ¹ |

¹ **Panne du banc mail, pas de l'application.** Le pod Toxiproxy du cluster (192.168.1.69) a redémarré vers
17:27 UTC (+5 310 s ; régime du palier 1400 depuis +4 568 s) et ses proxies ont disparu : IMAP et SMTP en
`ConnectionRefused` jusqu'à la fin du tir. Statuts k6 du palier 1400 (Prometheus `k6_http_reqs_total`) :
**avant la panne** (17:14:40 → 17:26:30 UTC) ≈ 201 654 réponses 200, **0** 5xx, 7 échecs réseau au relais du
poste (`dial i/o timeout`, 0,004 %) ; **après** ≈ 6 934 × 503 et ≈ 11 328 × 500. Le palier 1996 est VOID. Les
500 de la panne (`dashboard`, `read_list`) sont des pannes IMAP rendues en 500, le périmètre de task-425.

### p95 par étape, 200 → 1000 (ms, jambe A → jambe B)

| # | Étape | 200 | 400 | 700 | 1000 | Pire écart |
|---|---|---|---|---|---|---|
| 1 | Arrivée dashboard | 507 → 509 | 507 → 513 | 523 → 517 | 525 → 525 | +1,2 % |
| 2 | Inbox | 61 → 54 | 68 → 63 | 85 → 76 | 112 → 88 | −7 % |
| 3 | Message enrichi (servi base) | 42 → 41 | 47 → 46 | 60 → 52 | 82 → 60 | −2 % |
| 4 | Message froid | 510 → 505 | 509 → 514 | 514 → 513 | 525 → 516 | +1,0 % |
| 5 | Recherche | 596 → 608 | 606 → 579 | 651 → 634 | 643 → 630 | +2,0 % |
| 6 | Envoi | 913 → 921 | 914 → 919 | 921 → 917 | 931 → 927 | +0,9 % |
| 7 | Télécharger une PJ | 778 → 697 | 942 → 711 | 969 → 716 | 991 → 737 | −10 % |
| 8 | Marquer lu | 75 → 75 | 77 → 78 | 84 → 81 | 99 → 86 | +1,3 % |
| 9 | Rechercher un patient | 63 → 63 | 64 → 65 | 70 → 68 | 81 → 71 | +1,6 % |
| 10 | Page dossier patient | 65 → 66 | 69 → 73 | 80 → 78 | 103 → 86 | +5,8 % |
| 11 | Fiche patient complète | 343 → 367 | 364 → 392 | 417 → 416 | 531 → 451 | **+7,7 %** |

`cl_waiting` sur les bases praticien : 0 % des relevés à tous les paliers, dans les deux jambes.

### Verdict

- **Le mur recule** : 1,04 backend par actif au palier 1000 (critère < 1,6), et 0 erreur applicative au palier
  1400 tant que le banc mail a tenu (12 min de régime sur 16). ✅
- **Aucune étape ne se dégrade de plus de 20 %** entre 200 et 1000 : pire écart +7,7 % (fiche patient à 400). ✅
- **Jambe B acceptée, jambe C sans objet.** `pgbouncer.ini` porte `default_pool_size = 1` et son commentaire
  de mesure, qui dit aussi pourquoi l'A/B `mixed` du 2026-07-27 l'avait écarté.
- **Nouveau mur estimé** : (2 500 − 30 directs) ÷ 1,04 ≈ **2 400 médecins actifs**, contre ≈ 1 300. Estimation,
  pas une mesure : le palier 1996 du tir est VOID.

### Iso-conditions

| Condition | Jambe A | Jambe B | Écart |
|---|---|---|---|
| Lignée de code (`git log`, manifeste k6) | `892b571a` (+ faux fournisseur d'IA non commité) | `e31fac4d` = `892b571a` + `4c497985` « Fake IA provider » + task-423 | task-423 : gestion d'erreurs, hors chemin nominal |
| Bases | 1996 boîtes hydratées | mêmes bases, sans purge, plus âgées d'un tir | réserves froides en partie consommées par A (étapes 3 et 4 à lire avec prudence) |
| Tireur | k6bench, k6 v2.1.0 | idem | — |
| Banc mail | cluster 192.168.1.69 | idem, redémarré avant le tir (proxies recréés) | panne Toxiproxy à +5 310 s |
| `LATENCY_MS` | 96 | 96 | — |
| IA | 🧪 simulée | 🧪 simulée | — |
| Escalier | 6 × 18 min, K = 1, `JOURNEY_WARMUP_HYDRATED=1` | idem | — |

## Recommandation pour la production (à reporter par l'humain dans `DevOps`)

> Cible : `DevOps/DIMENSIONNEMENT-POSTGRESQL-API-MAIL.md`. La forge n'écrit pas dans `DevOps`.

- **PgBouncer** : `default_pool_size = 1`, `reserve_pool_size = 1`, `reserve_pool_timeout = 3`,
  `max_db_connections = 3`, `pool_mode = transaction` (les autres réglages sont inchangés).
- **Loi de dimensionnement mesurée** : backends ≈ **1,04 × médecins actifs** + ≈ 30 connexions directes
  (journal d'audit, provisionnement), contre 1,9 × actifs avec `default_pool_size = 2`.
- **Population visée** : 10 000 inscrits, soit ≈ 850 à 950 actifs (modèle terrain). Il faut ≈ 950 × 1,04 + 30 ≈
  **1 020 backends**. Recommandation : **`max_connections = 1 500`** (marge ≈ 45 % pour les rafales de la réserve
  et la croissance du parc). Pour comparaison, `default_pool_size = 2` en aurait demandé ≈ 1 835 sans marge.
- **Mémoire Postgres** : au banc, `shared_buffers` = 12 Go et le conteneur est plafonné à 48 Go. Son cgroup monte
  à 72 % (≈ 34 Go) à 1000 actifs dans la jambe B, soit ≈ 21 Mo par backend au-delà de `shared_buffers`. C'est
  une borne haute, car le cgroup compte aussi le cache de pages. C'est cohérent avec task-296 : ≈ 50 Go pour
  ≈ 2 000 backends. Pour ≈ 1 020 backends, prévoir **≥ 40 Go** pour l'instance Postgres
  (12 Go de `shared_buffers` + ≈ 22 Go de backends + marge).
- **Limite** : ces chiffres viennent d'un banc à IA simulée et à une base par boîte. Un premier relevé de
  `pg_stat_activity` en production, rapporté au nombre de médecins actifs, confirmera le 1,04.

## Develop log

- **2026-11-05 — premier passage interrompu** : banc injoignable (cluster et k6bench hors ligne),
  `questions/task-422.md`. Banc relancé par l'humain, puis proxies Toxiproxy recréés et service `iphlpsvc`
  relancé (relais `netsh portproxy` du poste).
- **Changement** : `Api/Mail/src/AppHost/pgbouncer/pgbouncer.ini`, `default_pool_size = 2 → 1`, commentaire de
  mesure réécrit. Aucun code applicatif (DoD) : pas de test d'intégration à prouver (règle 1b sans objet, aucun
  comportement d'endpoint ne change).
- **Tir** : jambe B, voir plus haut. Rapport généré par `report.sh` puis annoté (analyse en tête), ligne
  annotée dans `reports/INDEX.md`.
- **Incident de banc pendant le tir** : redémarrage du pod Toxiproxy du cluster vers 17:27 UTC, proxies perdus.
  Diagnostiqué par le journal k6 (`ConnectionRefused` IMAP et SMTP en bloc) et par `GET :30474/proxies` = `{}`.
  Proxies recréés après le tir : `dotnet run --project tests/mss.mail.loadtest.seed -- --users 2000 --messages 0
  --mail-host 192.168.1.69 --registry "…Database=mss_registry_loadtest"`. Sans `--registry`, le seed refuse
  d'écrire dans le registre de dev (garde correcte).
- **Archivage** : `reports/` est ignoré par git (seuls les index sont versionnés). Les deux rapports sont copiés
  dans le plan de contrôle : `Docs/audits/api-mail-loadtest-journey-escalier-ia-simulee-20261105.md` (jambe A) et
  `Docs/audits/api-mail-loadtest-journey-escalier-task422-pool1-20261105.md` (jambe B).
- **Validation** (`api-mail`, branche à `e31fac4d` + `pgbouncer.ini`) : build 0 erreur, 0 avertissement ; tests
  domain 202, infrastructure 700, application 4 003, api 1 357, intégration 1 105 (+16 ignorés), **0 échec**,
  aucun `FATAL`, totaux identiques à task-423.

## Sonar log

- **Mode A (chaîné)**, `api-mail` sur `feat/task-422-mur-des-connexions-postgres-moins-de`. Le diff de la task ne
  porte aucun C# (`pgbouncer.ini`, exclu de l'analyse avec `**/AppHost/**`) ; analyse jouée quand même, le
  playbook ne prévoyant le skip que sans commit.
- **Itération 1** : 1 issue new code, `external_roslyn:CA1861` (INFO) dans
  `tests/mss.mail.api.tests/E2e/FakeOpenAiTests.cs:105`, venue du commit « Fake IA provider » (`4c497985`, déjà
  sur `develop`, dans la période new code). Corrigée par refactor pur : tableau hissé en
  `static readonly string[] UrgencyTagNames` (`a51b1926`). Build vert, `mss.mail.api.tests` 1 357/1 357.
  Récidive consignée dans `conventions/csharp.md` (CA1861, occurrences 5 → 6).
- **Itération 2** : 0 issue new code, Quality Gate OK. Tests sous couverture : 202 + 4 003 + 700 + 1 357 + 1 105
  (+16 ignorés), 0 échec.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | = |
| Issues new code | 1 (CA1861) | 0 | −1 |
| New coverage | 96,0 % | 96,0 % | = |
| Bugs / Vulnérabilités / Code smells | 0 / 0 / 1 | 0 / 0 / 0 | −1 smell |
| Security hotspots | 0 | 0 | = |
| Coverage projet | 97,8 % | 97,8 % | = |
| Duplication | 0,4 % | 0,4 % | = |
| Ratings fiabilité / sécurité / maintenabilité | A / A / A | A / A / A | = |

> La baseline lue avant le premier scan (Quality Gate OK, 0 issue) datait de l'analyse de task-423 ; l'issue
> CA1861 n'est apparue qu'au premier scan de cette branche, qui inclut `4c497985`.

## Lint log

- `/lint-angular` : **skipped** — `client-angular` n'est pas dans les `**Repos**` de la task.
- `/lint-mobile` : **skipped** — `client-mobile` n'est pas dans les `**Repos**` de la task.

## E2E log

| Voie | Déclenchée par | Résultat | Durée |
|---|---|---|---|
| mobile (`npm run e2e:headless`) | `api-mail` touché | ✅ 58 verts, 0 flaky, 0 rouge, parité verte | 8,3 min |
| angular (`npm run e2e:mss`), 1er passage | `api-mail` touché | ❌ 65 verts, **6 rouges** : outillage, voir ci-dessous | 8,1 min |
| angular, rejeu unique | — | ✅ 71 verts, 0 flaky, 0 rouge, parité verte | 8,9 min |

**Premier passage Angular, rouge d'outillage.** Les 6 tests rouges étaient tous les tests Weda embarqué
(E2E-WEDA-001/002/003, E2E-MAILBOX-001 embarqué, E2E-SESSION-001, E2E-SESSION-003). Ils sont tombés à l'identique
au second essai Playwright, sur la même erreur : `listen EADDRINUSE :::47399` dans `support/weda-host.ts:385`. Le
port 47399 est celui de l'hôte Weda factice de la suite (`FAKE_HOST_ORIGIN`). Un processus extérieur à la suite
le tenait pendant ce passage. Il était libre à la fin du passage, et libre au départ du rejeu
(`netstat` consigné). Pendant le rejeu, seul le processus de la suite l'a tenu. Le processus fautif n'a pas
pu être identifié, faute de relevé pendant le premier passage. Le diff de la task (`pgbouncer.ini`, un test C#)
ne touche aucun de ces parcours. Voie rejouée **une fois**, porte jouée sur le rejeu. Rapport du premier passage
conservé : `$TEMP/forge-e2e/task-422/angular-report-1-eaddrinuse.json`.

**Porte** (`mss.mail.e2e gate`, catalogue `Api/Mail/e2e/scenarios.yml` inchangé face à `origin/develop`) :

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-PATIENT-003 | 1 | headless | La fiche d'un patient ne montre pas les documents d'un autre patient du même mail | ✅ | ✅ |
| E2E-PATIENT-004 | 1 | headless | La vue « Mails du patient » reste ouverte et ses pages viennent du serveur | ✅ | — |
| E2E-CONTACT-001 | 2 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 3 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-COMPOSE-004 | 1 | headless | Écrire à l'adresse choisie d'un contact à plusieurs adresses, ou à son adresse par défaut | ✅ | ✅ |
| E2E-COMPOSE-005 | 1 | headless | Une remise incertaine n'est jamais présentée comme un échec à renvoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-MAIL-006 | 1 | headless | Glisser sur la Corbeille un message d'un fil supprime ce message, et lui seul | ✅ | — |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-DRAFT-003 | 1 | headless | Quitter une rédaction récente ne perd rien | ✅ | ✅ |
| E2E-DRAFT-004 | 1 | headless | Une rédaction sans texte dans le corps ne laisse ni brouillon ni question | ✅ | ✅ |
| E2E-BIO-001 | 2 | headless | Acquitter un compte rendu de biologie, à son nom | ✅ | ✅ |
| E2E-BIO-002 | 1 | headless | La puce « Bio à acquitter » montre tous les résultats en attente, sur toutes les pages | ✅ | ✅ |
| E2E-BIO-003 | 1 | headless | Lire un résultat HPRIM puis l'acquitter | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SETTINGS-004 | 1 | headless | Paramètres indisponibles : rien n'est écrasé | ✅ | — |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 2 | headless | Créer un contact à deux adresses, le modifier sans les perdre, puis le supprimer | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-CONTACT-004 | 1 | headless | Consulter un contact depuis le carnet et lui écrire | ✅ | ✅ |
| E2E-CONTACT-005 | 1 | headless | Une fiche modifiée ne se perd pas sans confirmation, une adresse mal formée est refusée | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 2 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-MAILBOX-002 | 1 | headless | api-mail indisponible à l'entrée — écran de panne puis réessai | ✅ | ✅ |
| E2E-MAILBOX-003 | 2 | headless | Rattacher ses boîtes depuis « Mes boîtes » en un geste — titulaire et membre | ✅ | ✅ |
| E2E-MAILBOX-006 | 1 | headless | Après le rattachement, l'identité d'expéditeur et la signature sont déjà là | ✅ | ✅ |
| E2E-MAILBOX-004 | 1 | headless | Ajouter une BAL déléguée par saisie — et refus de sa propre adresse | ✅ | ✅ |
| E2E-MAILBOX-005 | 1 | headless | Le délégataire refusé par l'opérateur perd l'accès, en ligne puis hors ligne ; le titulaire garde le sien | ✅ | ✅ |
| E2E-AUDIT-001 | 1 | headless | Le titulaire lit au journal le message supprimé par son délégataire, au nom du délégataire | ✅ | — |
| E2E-AUDIT-002 | 1 | headless | Le journal d'audit montre chaque action sur un mail | ✅ | — |
| E2E-SHARED-001 | 1 | headless | Une boîte partagée, une base — le patient rattaché par le titulaire est vu du délégataire, la signature reste à chacun | ✅ | ✅ |
| E2E-SHARED-002 | 1 | headless | Le délégataire écrit pour le compte du titulaire — le destinataire voit qui a écrit, sa réponse revient à la boîte | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |
| E2E-SESSION-004 | 1 | headless | Sur un appareil partagé, la personne suivante n'arrive jamais dans la boîte de la précédente | ✅ | ✅ |
| E2E-AI-002 | 1 | headless | Un délégataire interroge l'assistant dans la boîte qu'il a ouverte | ✅ | ✅ |
| E2E-MAILBOX-007 | 1 | headless | Après un changement de boîte, l'onglet Patients ne montre plus rien de la précédente | ✅ | ✅ |
| E2E-ERROR-001 | 1 | headless | Une erreur affiche un code et une référence à transmettre au support | ✅ | ✅ |

**Parité : verte** — aucun écart entre le catalogue et les suites.

- Démontage vérifié : ports e2e libres. Aucun conteneur laissé par ce run. Les deux conteneurs anciens
  `e2e-greenmail-gcgjbrzp` et `e2e-dovecot-kgrndjwd`, déjà signalés à task-423, sont toujours là : à supprimer par l'humain.
- Quarantaine E2E-COMPOSE-002 (task-350) : **passée** à ce run. Posée depuis environ 4 semaines, elle est à
  retirer par l'humain si task-350 est soldée.

## PRs

- `api-mail` : [#341](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/341) — `awaiting-human-merge`.
  Branche `feat/task-422-mur-des-connexions-postgres-moins-de`, à jour avec `develop` (aucune fusion nécessaire).
- `devops` : la recommandation pour la production (section ci-dessus) est à reporter par l'humain.

## Code Review Summary

**APPROVED** — 4 fichiers relus, 0 bloquant, 1 suggestion.

- **Validation** : build 0 erreur, 0 avertissement ; tests domain 202, infrastructure 700, application 4 003, api 1 357,
  intégration 1 105 (+16 ignorés), 0 échec.
- **DoD** :
  - build et tests ✅ ;
  - jambe B tirée et rapport rangé : `reports/` est gitignoré, le rapport est archivé dans `Docs/audits/` ✅ ;
  - table palier par palier et écarts par étape ✅ ;
  - verdict ✅ ;
  - jambe C sans objet ✅ ;
  - `pgbouncer.ini` ✅ ;
  - recommandation pour la production ✅ ;
  - iso-conditions ✅ ;
  - aucun code applicatif ✅, la seule ligne C# est un refactor de test (CA1861) ;
  - données synthétiques ✅.
- **Règle 1b** : sans objet. Aucun comportement atteignable par un endpoint ne change : réglage du pooler de banc,
  aucune ligne de `src/` hors `AppHost/pgbouncer`.
- **E2E** : vert. Mobile 58/58. Angular 71/71 au rejeu, après un premier passage rouge d'outillage (port 47399 pris).
  Parité verte.
- ⚠️ **Suggestion** : le mur de ~2 400 actifs est une estimation. Un tir dont le palier haut tient le confirmera.

## Timings

*(généré par `tools/timing/report.sh --task task-422 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 23 s | — | — | — | — |
| /develop | ok | 6 min 31 s | 1 (13 s) | 1 (5 min 29 s) | — | api-mail 1B/1T, jambe B acceptée ; §Q sans objet (diff = réglage + commentaire) |
| /sonar | ok | 17 min 57 s | 3 (1 min 04 s) | 12 (13 min 35 s) | 4 (1 min 28 s) | 2 itération(s), api-mail 3B/12T |
| /lint-angular | skipped | 0.6 s | — | — | — | client-angular non listé dans Repos |
| /lint-mobile | skipped | 0.5 s | — | — | — | client-mobile non listé dans Repos |
| /e2e | ok | 29 min 07 s | — | — | — | e2e ×9 (54 min 34 s), mobile vert ; angular rejoué une fois (EADDRINUSE 47399, outillage) puis vert ; porte verte |
| /review | ok | 6 min 13 s | 1 (13 s) | 1 (5 min 23 s) | — | api-mail 1B/1T |
| /tech-writer | ok | 31 s | — | — | — | — |
| **Total cycle** | | **1 h 00 min** | **5 (1 min 31 s)** | **14 (24 min 28 s)** | **4 (1 min 28 s)** | |
