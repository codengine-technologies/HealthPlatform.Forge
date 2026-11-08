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
