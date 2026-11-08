# todo-task-435.md — Banc : l'attente PgBouncer ventilée par famille de base, puis qualifiée

**Repos**: api-mail
**Dependencies**: — (aucune)
**Epic**: E015
**Single frontend**: true
**Priorité**: **2**, demandée par l'humain le 2026-11-08 après le bilan du lot 426-432 : « instruire l'attente
PgBouncer avant d'optimiser ». C'est la **limite suivante** désignée par la synthèse. Or l'instrument qui devait la
qualifier est **cassé depuis le 2026-10-29**. Cette task le répare, puis mesure. Elle ne change aucun réglage.

> **Origine.** Synthèse `Docs/audits/api-mail-loadtest-ab-bilan-lot-20261108.md`, « Ce qui reste », point 1 :
> `cl_waiting` non nul sur 16 % des relevés à 1400 et 34 % à 1996 au tir `bilan-apres` (code `5b4e394f`). Il était à
> 28 % et 60 % sous le code d'avant le lot. Le contrat du rapport exige zéro.

## Ce qui est établi

- **La ventilation par famille de pool est fausse depuis task-404** (« une base par boîte », mergée le 2026-10-29).
  - task-242 a séparé l'attente PgBouncer en deux familles : les bases **praticien** (le chemin de données du
    médecin) et le pool de **maintenance** (`postgres`, alors traversé par la sonde de readiness).
  - Le filtre qui reconnaît une base praticien est `^u_9\d` (`tests/loadtest-k6/observe.ps1:511`), le RPPS
    synthétique du banc.
  - Depuis task-404, le nom de base ne porte plus le RPPS : il vaut `u_{slug}_{sha256(adresse)[:32]}`, soit
    `u_l9l_…` au banc. `reset-state.sh` a été corrigé à ce moment (voir son en-tête, « PORTÉE »), mais pas
    `observe.ps1` ni `report.py`.
  - **Conséquence** : depuis le 2026-10-29, chaque pool praticien est compté en « maintenance ». Les trois rapports du
    2026-11-08 affichent :
    - « …dont bases **praticien** : 0 % » ;
    - « …dont pool de **maintenance** (`postgres`) — sonde de readiness : 16 % / 34 % », profondeur jusqu'à 205 ms.

    Les deux lignes sont fausses. La sonde de readiness ne traverse plus le pooler depuis task-249
    (`ServerConnectionString.ResolveProbeRoute`). L'attente mesurée est donc, selon toute vraisemblance, celle des
    **bases praticien, sur le chemin du médecin**. C'est non prouvé tant que la ventilation est cassée.
- **Deuxième instrument éteint par la même cause** : la sonde de login PostgreSQL depuis le conteneur
  (`observe.ps1:684-702`) cherche sa base cible par `u_9…`. Elle ne trouve rien, et le rapport affiche
  « Login PostgreSQL depuis le conteneur : non relevé » depuis la même date.
- **Ce qu'on sait du coût, et sa limite** : au tir `bilan-apres`, `GetMailsByUids` attribue 0,1 ms sur 83,0 ms à
  « l'attente d'une connexion ».
  - En mode transaction, l'attente d'un serveur PgBouncer survient à la **première requête** de la transaction, pas à
    l'ouverture de la connexion Npgsql.
  - Elle tombe donc probablement dans « exécution SQL ». C'est **non vérifié** : ce 0,1 ms ne prouve pas que
    l'attente est gratuite.
- **Ce que donne PgBouncer et que le banc ne relève pas** : `SHOW STATS` expose, par base, le temps d'attente cumulé
  des clients (`total_wait_time`) et le nombre de transactions. C'est la grandeur qui chiffre le coût, là où
  `cl_waiting` n'en dit que la présence, et `maxwait` la profondeur.
- **Récidive d'outillage** : un renommage des bases a été reporté dans un outil du banc, et pas dans les autres. Rien
  ne confronte les filtres des outils au nommage réel. L'échec est silencieux : une ligne « 0 % » ou « non relevé »,
  jamais une erreur.

## Objective

Le banc dit, par famille de base, combien de demandes attendent une connexion PgBouncer, combien de temps, et ce que
cette attente coûte au médecin. La limite suivante est qualifiée par la mesure avant tout réglage.

Règles :
- **Trois familles, reconnues par un seul critère partagé** :
  - **praticien** : toute base `u_…`, les deux nommages (`u_9…` d'avant task-404 et `u_{slug}_{hash}`), comme le
    compteur `practitioner_databases` du même script (`datname like 'u\_%'`) ;
  - **registre** : `mss_registry…`. Il est lu à chaque requête (FND-006), donc sur le chemin du médecin, et il est
    rendu à part ;
  - **maintenance** : le reste (`postgres`, `pgbouncer`).

  Le libellé du rapport nomme ce qu'il mesure. Plus de « sonde de readiness » affirmée sans preuve.
- **Le coût, pas seulement la présence** : l'échantillonneur relève `SHOW STATS` (`total_wait_time`, transactions,
  requêtes) et l'agrège par famille. Le rapport rend, par palier et par famille :
  - la présence (`cl_waiting` non nul) ;
  - la profondeur (`maxwait`, pire relevé et p95) ;
  - le **temps d'attente cumulé**, rapporté au nombre de transactions et au temps serveur des requêtes HTTP du palier.
- **La sonde de login revit** : elle trouve sa base cible quel que soit le nommage.
- **Le jugement porte sur le chemin du médecin** :
  - la ligne de tête « des demandes ont attendu une connexion » est jugée sur les familles praticien et registre ;
  - de même pour le signal « ressource épinglée » et le drapeau « soutenu » ;
  - une attente de la seule maintenance est rendue, sans alerte sur le parcours.
- **Une seule définition de « base praticien »** pour tous les outils du banc (échantillonneur, rapport,
  `reset-state.sh`), ou un test qui les confronte au nommage produit par le code. Un renommage futur doit faire
  échouer un test, pas éteindre une ligne du rapport.
- **Aucun réglage changé** : ni `default_pool_size`, ni `reserve_pool`, ni code de l'API. Le remède éventuel est une
  task distincte, décidée par l'humain sur la mesure de celle-ci.

### Hors périmètre

- Tout réglage de PgBouncer ou de Npgsql, et toute modification du code de l'API.
- Le temps IMAP de l'arrivée sur le dashboard (61 % du temps serveur de l'étape) : sujet distinct, point 3 de la
  synthèse.
- La garde VOID sur le SMTP du banc dans `report.py` : point 3 des décisions de la synthèse, autre task.
- Régénérer les rapports archivés avant le 2026-11-08 : ils sont signalés, pas recalculés (le détail par pool n'a
  pas été conservé).

## Definition of Done

- [ ] Tests de l'outillage du banc verts : `python -m pytest Api/Mail/tests/loadtest-k6` (ou la commande du README du
      banc) et `node --test lib/*.test.mjs`
- [ ] Build et tests de `HealthPlatform.Api.Mail.sln` verts (aucun code de l'API ne change ; le build le confirme)
- [ ] **Classement des pools, test vu rouge** : un test fournit des lignes `SHOW POOLS` portant les deux nommages de
      base praticien, le registre, `postgres` et `pgbouncer`. Il vérifie le classement en trois familles. Il est vu
      rouge sur le filtre `^u_9\d` actuel (une base `u_l9l_…` classée en maintenance).
- [ ] **Une seule définition, ou une confrontation testée** : la reconnaissance d'une base praticien est partagée par
      l'échantillonneur, le rapport et `reset-state.sh`. À défaut, un test confronte chacun de leurs filtres aux noms
      produits comme `UserContextInfo.ProposeDatabaseName` pour des identités du banc. Ce test est vu rouge sur le
      code actuel.
- [ ] **Sonde de login rétablie** : test qui montre qu'elle choisit une base `u_l…`. Au tir de mesure, la ligne
      « Login PostgreSQL depuis le conteneur » est renseignée.
- [ ] **Coût de l'attente relevé** : `SHOW STATS` est échantillonné et agrégé par famille (temps d'attente cumulé,
      transactions). Le rapport rend, par palier et par famille :
      - présence ;
      - profondeur (pire relevé et p95) ;
      - temps d'attente cumulé ;
      - attente moyenne par transaction ;
      - part du temps serveur HTTP du palier.

      Ce rendu est couvert par un test de `report.py` sur un CSV d'échantillons.
- [ ] **Jugement sur le chemin du médecin** : la ligne de tête « attendu une connexion », la « ressource épinglée » et
      le drapeau « soutenu » ne se déclenchent que sur les familles praticien et registre. Un test de rapport le prouve
      avec une attente de maintenance seule (pas d'alerte) et une attente praticien (alerte).
- [ ] **Où tombe l'attente dans les phases SQL** : le task file consigne, mesure à l'appui, si une attente PgBouncer
      apparaît dans « attente d'une connexion » ou dans « exécution SQL » de la table des phases. Le libellé ou la
      note de cette table est corrigé en conséquence.
- [ ] **Tir de qualification** : tir court 1400 → 1996 sur `develop`, IA simulée, pool 1, tireur k6bench, banc
      cluster, `LATENCY_MS=96`. Il est joué sur les bases hydratées du 2026-11-08, sans `reset-state`, avec
      l'outillage corrigé. Le compte rendu donne :
      - par palier et par famille : présence, profondeur et coût de l'attente ;
      - la continuité avec le tir `bilan-apres` : la présence totale `cl_waiting`, indépendante de la ventilation,
        doit retomber dans le même ordre (16 % / 34 %), sinon l'écart est expliqué ;
      - les étapes du parcours où l'attente pèse le plus, si la mesure permet de l'attribuer ;
      - le rapport copié dans `Docs/audits/`.
- [ ] **Décision préparée pour l'humain, sans rien appliquer**. Le seuil de reprise de task-242 est confronté à la
      mesure : attente praticien supérieure à 1 % du temps serveur d'une étape, ou profondeur p95 supérieure à 100 ms à
      un palier.
      - **Franchi** : la note propose les remèdes possibles, chacun avec son effet attendu et son risque (taille de
        pool, `reserve_pool`, nombre de transactions par requête, durée de détention), et l'A/B qui les départagerait.
      - **Non franchi** : la note le dit, et la limite suivante est désignée.
- [ ] **Rectification des comptes rendus**. Une note en tête de la section « Coûts résidents » des trois rapports du
      2026-11-08, dans `Docs/audits/`, et un renvoi dans la synthèse du bilan, disent que la ventilation praticien /
      maintenance et la sonde de login sont fausses depuis le 2026-10-29, et pourquoi. Les rapports du banc
      postérieurs au 2026-10-29 sont listés dans la note (lus dans `reports/INDEX.md`).
- [ ] **Prévention (règle d'or)** : le piège est consigné dans le README du banc (`tests/loadtest-k6/README.md`). Un
      renommage des bases se reporte dans tous les outils, et le test de confrontation le garantit. Le skill de banc
      (`.claude/skills/loadtest-skill/SKILL.md`) cite la grandeur de coût à lire, au lieu de la seule présence
      `cl_waiting`.
- [ ] Aucune donnée de santé en clair dans les logs, ni dans les rapports de banc (les noms de base du banc sont des
      empreintes d'adresses synthétiques `loadtest.local`)

## Manual Test Plan

- [ ] Lire la section « Coûts résidents » du rapport du tir de qualification. Vérifier que :
      - les trois familles (praticien, registre, maintenance) ont chacune leurs lignes ;
      - la famille praticien porte l'essentiel de l'attente, ou la note explique le contraire ;
      - la ligne « Login PostgreSQL depuis le conteneur » est renseignée.
- [ ] Vérifier que la ligne de tête du rapport et la « ressource épinglée » parlent du chemin du médecin, avec le coût
      de l'attente et pas seulement sa fréquence.
- [ ] Lire la note de décision : seuil franchi ou non, et ce qui est proposé.
- [ ] Ouvrir les rapports du 2026-11-08 dans `Docs/audits/` : la note de rectification est en tête de « Coûts
      résidents ».
- [ ] Facultatif : sur le banc lancé, renommer à la main une base de test dans un échantillon de `SHOW POOLS` fourni au
      test de classement. Le test doit échouer pour un nommage inconnu.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — outillage de mesure du banc de charge, hors produit
- **Vague Ségur** : hors Ségur — même raison
- **Exigences DSR honorées** : non applicable — aucun comportement du produit ne change
- **INS** : non applicable — aucune donnée patient manipulée
- **Authentification PS** : non applicable — aucune route ni authentification touchée. Le banc utilise ses identités
  synthétiques.
- **Habilitations** : non applicable — même raison
- **Interop CI-SIS** : non applicable — aucun échange
- **Tracé PGSSI-S** : inchangé — aucun acte du produit n'est ajouté ou modifié
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non — banc de charge local, données synthétiques (`loadtest.local`), aucune donnée de santé
  réelle
- **AIPD / impact RGPD** : inchangée — aucun traitement nouveau de données personnelles

## Branches

- `api-mail` (pushed) : fix/task-435-banc-attente-pgbouncer-ventilee-par — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-435-banc-attente-pgbouncer-ventilee-par

> Pré-flight du /start (2026-11-08) : `api-mail`, `client-blazor`, `client-mobile`, `dtos-mss`, `sdk` sur `develop`, arbres
> propres. `host` (`Host/Modules`) et `interop` ne sont pas des racines de dépôt (`--show-prefix` non vide) : connu, non
> bloquant. La task touche l'outillage du banc (`tests/loadtest-k6/`) et le plan de contrôle (`Docs/audits/`, skill de
> banc) : aucun autre dépôt.

## Timings

*(généré par `tools/timing/report.sh --task task-435 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 22 s | — | — | — | — |
| /develop | ok | 1 h 16 min | 4 (45 s) | 6 (1 min 18 s) | — | api-mail 4B/6T |
| /sonar | ok | 9 min 42 s | 1 (30 s) | 5 (7 min 44 s) | 2 (44 s) | 1 itération(s), api-mail 1B/5T |
| /lint-angular | skipped | 0.5 s | — | — | — | client-angular non touché |
| /lint-mobile | skipped | 0.6 s | — | — | — | client-mobile non touché |
| **Total cycle** | | **1 h 26 min** | **5 (1 min 15 s)** | **11 (9 min 03 s)** | **2 (44 s)** | |

Autres commandes mesurées : capture ×1 (50 min 32 s)

## Qualification de l'attente PgBouncer — décision préparée

> - **Tir** : `journey-courte-1400-1996-20261108-t435-qualif`, api-mail `develop` (`a7d8429f`), outillage de task-435
>   (`55c51ca5`).
> - **Conditions** : IA simulée, pool 1, tireur k6bench (75,6 Mo/s), banc mail cluster, `LATENCY_MS=96`, bases
>   hydratées du 2026-11-08 sans `reset-state`.
> - **Validité** : SMTP sain (220 ms pour une session), 0,012 % d'erreurs, chauffe aboutie.

### Qui attend

| Famille de base | Présence (`cl_waiting` non nul) 1400 / 1996 | Profondeur `maxwait` p95 / pire, 1400 / 1996 |
|---|---|---|
| **bases praticien** (chemin du médecin) | 21 % / 35 % | 11,2 / 46,0 ms — 11,6 / 152,9 ms |
| registre des comptes | 0 % / 0 % | 0 |
| maintenance (`postgres`, `pgbouncer`) | 0 % / 0 % | 0 |

- **Toute l'attente est sur les bases praticien, donc sur le chemin du médecin.** La lecture « sonde de readiness » des
  rapports d'avant était fausse : c'était le filtre de l'échantillonneur, pas le pooler.
- **La continuité tient.** La présence totale (21 % / 35 %) retombe dans l'ordre du tir `bilan-apres` (16 % / 34 %).
- Le registre ne passe par aucune file : ses 0 transactions via le pooler montrent qu'il est servi en direct.

### Ce qu'elle coûte

| Mesure (`SHOW STATS`, bases praticien + registre) | 1400 médecins | 1996 médecins |
|---|---|---|
| Attente cumulée sur le palier (1 060 s) | 728,5 s | 1 337,4 s |
| Clients en attente en moyenne (attente ÷ durée) | 0,7 | 1,3 |
| Transactions | 1 939 034 | 2 801 236 |
| Attente par transaction | 0,4 ms | 0,5 ms |
| Part du temps des transactions (attente comprise) | 18,3 % | 19,2 % |
| Part du temps des requêtes HTTP du palier (k6) | 3,4 % | 3,2 % |

- **Une requête HTTP du parcours ouvre 10 à 12 transactions.** Chacune attend en moyenne 0,4 à 0,5 ms qu'un serveur se
  libère, soit environ 5 ms par requête.
- **Où l'attente apparaît dans les phases SQL** : dans « exécution SQL », pas dans « attente d'une connexion ».
  - `GetMailsByUids` porte 0,1 ms d'« attente d'une connexion » pour 14,7 requêtes par appel. Avec 0,5 ms
    d'attente PgBouncer par transaction, c'est de l'ordre de 7 ms par appel, invisibles dans cette colonne.
  - En mode transaction, le pooler attribue un serveur à la **première requête** de chaque transaction.
  - La note de la table des phases est corrigée dans le rapport et dans `report.py`.
- **Phénomène distinct, à ne pas confondre** : `GetMail` porte 4,3 ms d'« attente d'une connexion », soit 9,5 % de
  l'appel, au p95 64 ms. C'est le **pool Npgsql** de la base, et non PgBouncer.
- **Attribution par étape impossible** avec cet instrument : `SHOW STATS` compte par base, pas par route.

### Confrontation au seuil de reprise de task-242

| Critère | Seuil | Mesure | Verdict |
|---|---|---|---|
| Attente praticien rapportée au temps serveur | > 1 % | 3,2 à 3,4 % du temps HTTP mesuré par k6 (le temps serveur, plus court, en ferait une part plus grande) | **franchi** |
| Profondeur p95 à un palier | > 100 ms | 11,2 / 11,6 ms | non franchi |

**Le seuil est franchi par le coût, pas par la profondeur.** La file est **fréquente et courte** : un médecin dont
plusieurs requêtes arrivent ensemble (plusieurs réplicas, rafales du dashboard) les voit se sérialiser derrière l'unique
connexion serveur de sa base (pool 1, task-422).

### Remèdes possibles — à décider, aucun n'est appliqué

| Remède | Effet attendu | Risque | Ce qui le départagerait |
|---|---|---|---|
| **A. Moins de transactions par requête** (grouper les lectures d'une requête : `GetMail` 11 requêtes, `GetMailsByUids` 14,7) | moins d'attributions de serveur, donc moins d'attentes ; gain de latence au-delà de l'attente (allers-retours) | code applicatif, par chemin ; une transaction longue tient le serveur plus longtemps (pool 1) | A/B du tir court sur `GetMailsByUids` seul : attente cumulée et p50 des étapes 2 et 3 |
| **B. `reserve_pool_size` = 1, `reserve_pool_timeout` court** | absorbe les rafales sans doubler les backends en régime | backends en pointe, donc retour vers le mur `max_connections` (~1 300 actifs à pool 2, task-422) | A/B : attente cumulée, backends au pic, `max_connections` |
| **C. Pool 2** (retour d'avant task-422) | supprime l'essentiel de la file | **écarté** : 1,9 backend par actif, mur à ~1 300 actifs (mesuré le 2026-11-05) | — |
| **D. Continuer à réduire la durée des transactions** (findings SQL : FND-007 `HtmlBody`, FND-010, FND-014) | moins de temps de serveur occupé, donc moins d'attente | nul, déjà la voie suivie | déjà mesuré par les A/B de chaque finding |

**Ma recommandation** : **A d'abord**, sur le chemin le plus fréquent (`GetMailsByUids`, la page d'en-têtes). Elle
attaque la cause, le nombre d'attributions, sans toucher au plafond de connexions que task-422 a levé. B vient
ensuite, si A ne suffit pas, avec un A/B qui surveille les backends au pic.

**Limite suivante désignée**, quel que soit le choix : l'appel IMAP `GET /mail/folders/{folder}`, qui pèse 61 % du
temps serveur de l'arrivée sur le dashboard (synthèse du bilan du lot, point 3).

Rapport complet : `Docs/audits/api-mail-loadtest-journey-courte-1400-1996-t435-qualif-20261108.md`.

## Develop log

- **Repos touchés** : `api-mail`, outillage du banc (`tests/loadtest-k6/`) et un test C#, plus le plan de contrôle
  (rapports dans `Docs/audits/`, skill de banc). Aucun code applicatif (`src/` = `develop`), aucun réglage de
  PgBouncer.
- **Commits** (`fix/task-435-banc-attente-pgbouncer-ventilee-par`, poussés) :
  - `7c6715ea` fix(loadtest) : ventilation par famille, jugement sur le chemin du médecin, coût de l'attente ;
  - `17c1b0d6` docs(loadtest) : piège n° 7 du README ;
  - `55c51ca5` fix(loadtest) : la sonde de login vise une base du banc ;
  - `bf216c42` fix(loadtest) : l'attente PgBouncer tombe dans « exécution SQL » ; index du tir ;
  - `7c80b172` refactor(loadtest) : passe qualité (/simplify) ;
  - `44ea1038` test(loadtest) : base de développement fabriquée dans les tests.

### Ce qui a été fait

- **Une définition, `lib/db-families.json`** : familles praticien (`^u_`), registre (`^mss_registry`), maintenance
  (le reste), chacune avec son drapeau `doctor_path`, et un `bench_pattern` (`^u_l[0-9]l_`) pour viser les bases
  du banc.
  - Elle est lue par l'échantillonneur via `lib/db-families.ps1`, en fonctions pures : classement, `SHOW POOLS`,
    `SHOW STATS` lu par nom de colonne, deltas.
  - Elle est lue par `report.py` pour les familles du chemin du médecin.
- **`observe.ps1`** : `SHOW POOLS` ventilé en trois familles, plus `cl_waiting_doctor_path`. `SHOW STATS` donne des
  deltas par famille (`wait_us`, `xact`, `xact_us`). La sonde de login et le compteur de backends praticien suivent
  la définition.
- **`report.py`** :
  - l'alerte de tête, la ressource épinglée et « soutenu » se jugent sur le chemin du médecin, avec repli sur le
    total pour un CSV archivé, que la phrase de tête signale (« toutes bases confondues ») ;
  - lignes registre, et cinq lignes de coût : attente cumulée, par transaction, part des transactions, part des
    requêtes HTTP du palier, attente de la maintenance ;
  - la note de la table des phases est corrigée.
- **Nommage bash partagé** : `lib/bench-db-names.sh` remplace les copies de `reset-state.sh` et de `verify.sh`.
- **Défaut trouvé au tir de qualification, corrigé** : la sonde de login avait fixé sa cible sur une base de
  développement au préfixe praticien, hébergée par le même Postgres. Elle vise désormais `bench_pattern`.
- **Défaut trouvé par la passe qualité, corrigé** : les photos Postgres (`pg-connections.sh`, `pg-statements.sh`)
  et `verify.sh` portaient aussi leur copie du filtre ou du nommage. Le nommage est partagé, et les filtres
  `BENCH_LIKE` sont confrontés par test.

### Tests et preuves rouges

| Comportement | Test | Preuve rouge |
|---|---|---|
| Classement réel de l'échantillonneur sur `SHOW POOLS` : deux nommages praticien, registre, maintenance, chemin du médecin | `test_db_families.SamplerClassificationTests.test_show_pools_waiting_is_split_by_family` | ancien filtre `^u_9\d` réinjecté dans la définition : « 4 != 1 » (attente praticien comptée en maintenance), avec 4 autres tests rouges |
| `SHOW STATS` lu par nom de colonne, sommé par famille ; colonne absente = rien ; delta par famille, compteur qui recule écarté | `…show_stats…`, `…stats_delta…` | même mutation (stats praticien manquantes) |
| Les noms de l'application tombent en famille praticien et sous `bench_pattern` | `BenchDatabaseFamiliesTests` (C#) | ancien filtre : rouge (« boîte n° 1 … n'est pas reconnue ») ; `bench_pattern` faux : rouge |
| Le nommage bash du banc rend le nom exact de l'application | `test_the_shared_name_is_the_one_the_application_proposes` + `TheBenchNamingScript_ProposesTheSameNameAsTheApplication` (même littéral) | hachage tronqué à 31 caractères : rouge |
| La sonde de login ne vise pas une base de développement | `test_the_bench_pattern_keeps_the_login_probe_on_bench_bases` | `bench_pattern` trop large (`^u_`) : rouge |
| Les photos Postgres filtrent les bases du banc, et elles seules | `test_the_postgres_photos_filter_the_bench_bases` | — (confrontation ajoutée, verte : les filtres existants étaient justes) |
| Aucun script ne garde de copie du filtre ou du nommage | `ScriptTextTests` | rouge sur l'`observe.ps1` d'origine (trois filtres, aucune définition chargée) |
| Alerte de tête sur le chemin du médecin ; maintenance seule = pas d'alerte ; repli sur le total pour un CSV archivé | `test_report_pgbouncer_families.JudgedOnTheDoctorPathTests` | rouges sur le `report.py` d'origine (8 sur 8 avant code) |
| Lignes de coût (cumul, par transaction, parts) et « non relevé » sans `SHOW STATS` | `TheCostIsMeasuredTests` | rouges sur le code d'origine |

- Deux tests existants de `test_report_pinned_palier.py` figeaient la déclaration à deux familles. Ils déclarent
  désormais le registre : c'est le changement voulu par la task.

### Validation

- Harnais (`selftest.sh`, comme la CI) : 453 tests verts.
- Build `HealthPlatform.Api.Mail.sln` : 0 erreur, 0 avertissement. `api.tests` : 1 376/1 376 (+6).
- Aucun code applicatif ne change : les autres projets de tests ne sont pas rejoués ici, `/review` le fera.

### Passe qualité (§Q, /simplify, 4 axes)

- **Appliqué** :
  - nommage bash partagé ;
  - confrontation des `BENCH_LIKE` ;
  - `report.py` lit la définition ;
  - agrégat du chemin du médecin dans le module pur ;
  - séries mortes retirées ;
  - classement mémorisé par nom ;
  - tests PowerShell en un processus ;
  - `_sample_values` et `telemetry_for` réutilisés ;
  - commentaires périmés corrigés, récit de l'incident ramené au README.
- **Écarté, noté** :
  - lire `SHOW POOLS` et `SHOW STATS` en un seul appel `psql` (environ 100 ms par relevé de 5 s) : cela change la
    lecture de `SHOW POOLS`, à valider sur un tir ;
  - dériver les noms des bases du registre plutôt que de les recalculer en bash : le nom exact figé de part et
    d'autre confronte déjà les deux implémentations. À ouvrir en task si le nommage bouge encore ;
  - `bench_pattern` suppose le domaine par défaut (`loadtest.local`), ce que la définition dit.

### DOD — auto-contrôle

| Item | Statut |
|---|---|
| Tests du harnais et `node --test` | ✓ 453 Python ; Node 133/0 (fichiers `lib/*.test.mjs`) |
| Build et tests de la solution | ✓ build ; `api.tests` 1 376 ; reste rejoué par `/review` |
| Classement des pools, test vu rouge sur le filtre actuel | ✓ |
| Une seule définition, ou une confrontation testée | ✓ les deux : définition partagée, confrontée à l'application, à `reset-state.sh`, à `verify.sh` (nommage partagé) et aux `BENCH_LIKE` |
| Sonde de login rétablie | ✓ test du motif, et ligne renseignée au tir (9 à 11 ms au p50) |
| Coût de l'attente relevé et rendu, couvert par un test de `report.py` | ✓ |
| Jugement sur le chemin du médecin, test maintenance seule / praticien | ✓ |
| Où tombe l'attente dans les phases SQL, note corrigée | ✓ « exécution SQL » ; note corrigée dans `report.py` et dans le rapport |
| Tir de qualification, rapport copié | ✓ `Docs/audits/api-mail-loadtest-journey-courte-1400-1996-t435-qualif-20261108.md` |
| Décision préparée, sans rien appliquer | ✓ section « Qualification de l'attente PgBouncer » |
| Rectification des comptes rendus | ✓ note dans les 5 rapports du 2026-11-08, liste des 14 autres dans la synthèse |
| Prévention : README du banc, skill de banc | ✓ piège n° 7 ; encadré du skill (§ 5a-bis) |
| Aucune donnée de santé | ✓ noms de base = empreintes d'adresses synthétiques. Un test citait d'abord l'empreinte d'une base de développement réelle du poste : remplacée par un nom fabriqué (`44ea1038`). Elle reste dans deux commits intermédiaires de la branche, que le squash n'emporte pas sur `develop` |

## Sonar log

- SonarQube 9.9.8 (`sonar.login`), projet `healthplatform-api-mail`, une analyse complète de la branche.
- **Phase 1 (new code)** : ✓ Quality Gate OK, new_coverage = 96,0 %, 0 issue de code neuf, 0 hotspot.
- **Phase 2 (legacy)** : 0 itération, la dette préexistante est à zéro.
- **Build / tests** : ✓ verts (domaine 210, application 4 031, infrastructure 728, api 1 376, intégration 1 142 + 16
  ignorés).
- Aucune règle corrigée à la main : rien à verser dans `conventions/csharp.md`.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 95,9 % | 96,0 % | +0,1 pt |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 0 | 0 | 0 |
| Coverage (projet) | 97,9 % | 97,9 % | 0 pt |
| Duplication | 0,4 % | 0,4 % | 0 |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |
