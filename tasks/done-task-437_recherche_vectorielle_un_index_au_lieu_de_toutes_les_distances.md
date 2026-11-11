# todo-task-437.md — Recherche vectorielle : un index au lieu de toutes les distances

**Repos**: api-mail
**Dependencies**: — (aucune ; à coordonner avec task-440, qui change la fusion des résultats sémantiques)
**Epic**: E015
**Single frontend**: true
**Priorité**: demandée par l'humain le 2026-11-09, après le temps 1 du plan de volumétrie. Décisions de l'humain :
- **recherche approchée acceptée, sous plancher mesuré** : au moins 95 % des 10 premiers résultats identiques à la
  recherche exacte ;
- **deux tasks** : le plein texte est traité à part. D'abord task-436, elle a été **absorbée par task-439** le
  2026-11-09 (EPIC E022, refonte du plein texte), sur décision de l'humain.

> **Origine.** FND-010 du registre (`Docs/audits/findings-registry.md`), « plausible, à trancher par un tir sur des
> boîtes 10 fois plus grosses ». Tranché le 2026-11-09 par le temps 1 du plan de volumétrie :
> `Docs/audits/api-mail-volumetrie-plans-boite-11k-20261109.md`, plans et script dans
> `Docs/audits/findings/plans/20261109-volumetrie-boite-11k/`.

## Ce qui est établi

| Forme FND-010 (code `405da376`) | Boîte du banc (156 mails) | Boîte de 11 178 mails | Facteur |
|---|---|---|---|
| `90fed31c…` vectorielle sur `MailContents` | 2,23 ms, 715 pages | **295,88 ms, 70 439 pages** | **×133** |
| `9b0276b9…` vectorielle sur `MailMedicalDocuments` | 2,40 ms, 743 pages | 16,35 ms, 4 092 pages | ×6,8 |

- **Site** : `SemanticSearchRepository.SearchEmailContentsByVectorAsync` (ligne 179) et
  `SearchMedicalDocumentsByVectorAsync` (ligne 249), `src/Infrastructure/Repositories/MailDb/`, commit `405da376`.
  Appelés par chaque `POST /api/v1/Search/semantic` en mode sémantique ou hybride (`SemanticSearchService`).
- **Cause** : aucun index sur `Embedding`, dans aucune migration, et aucune décision ne l'écarte. Chaque recherche
  calcule la distance pour **toutes** les lignes de la boîte (`Seq Scan`), en relisant chaque vecteur depuis TOAST
  (6 148 octets, environ trois lectures de page par ligne) : environ 70 Mo relus par recherche sur la boîte de
  11 178 mails.
- **Sonde du 2026-11-09**, sur la boîte de 11 178 mails, dans une transaction annulée (`ROLLBACK`, base inchangée),
  pgvector 0.8.1 :
  - la colonne `Embedding` est un `vector` **sans dimension** : un index HNSW direct est refusé (« column does not
    have dimensions »). L'index sur l'expression `("Embedding")::vector(1536)` avec `vector_cosine_ops` est accepté ;
    la requête doit alors ordonner sur la même expression ;
  - construction : **1,6 s** pour les 11 284 contenus, 0,1 s pour les 567 documents (`maintenance_work_mem` 256 Mo) ;
  - taille : **88 Mo** pour les contenus (la base fait 182 Mo), 4 Mo pour les documents ;
  - requête ordonnée sur l'index, avec `hnsw.iterative_scan = relaxed_order` : **1,2 ms, 469 pages**, au lieu de
    296 ms et 70 439 pages ;
  - rappel des 10 premiers résultats contre la recherche exacte : **100 %** sur 30 requêtes. Limite : ces requêtes
    étaient des vecteurs de la boîte elle-même, pas des phrases de recherche.
- **Ce que la requête actuelle fait et que l'index change** : elle filtre sur `distance <= maxDistance` (0,9 au banc)
  avant de trier. Un index ne sert que si la requête **ordonne** sur la distance et limite ; le seuil devient un filtre
  appliqué aux résultats.
- **Déploiement** : une base est migrée à son **premier accès**, sous un **sémaphore commun à toutes les boîtes du
  processus** (`BaseRepository.HandleEnvironmentDbSetupAsync`, cache Redis `setupdb:` d'un jour). Construit dans une
  migration ordinaire, l'index retarderait l'ouverture de **toutes** les boîtes pendant la construction de chacune.
- **Stockage à l'échelle** : 88 Mo par boîte de 11 000 mails, soit de l'ordre de 0,9 To pour 10 000 médecins. Un index
  en demi-précision (`halfvec(1536)`) en pèserait environ la moitié ; il est à mesurer.

## Objective

Une recherche sémantique ne calcule plus la distance de chaque message et de chaque document de la boîte : elle passe
par un index. Son coût ne suit plus la taille de la boîte, et sa précision reste au-dessus du plancher fixé par
l'humain.

Règles :
- **Index sur les deux tables** : `MailContents` et `MailMedicalDocuments`, distance cosinus, sur l'expression typée
  imposée par la colonne sans dimension. La requête ordonne sur la même expression.
- **Plancher de précision (décision de l'humain)** : sur la boîte de 11 178 mails, au moins **95 %** des 10 premiers
  résultats sont identiques à ceux de la recherche exacte, en moyenne sur au moins 20 **vraies phrases de recherche**
  (embeddings calculés comme en production). En dessous, `/develop` règle l'index (paramètres de recherche,
  `ef_search`) ; s'il ne peut pas l'atteindre, il s'arrête sur `questions/task-437.md`.
- **Même sens pour le médecin** : le seuil de similarité, le dossier, le modèle d'embedding et le nombre maximal de
  résultats sont respectés comme aujourd'hui. Seule l'exactitude du classement devient approchée, dans le plancher.
- **La construction ne bloque pas les autres boîtes** : ni à la création d'une base, ni à la migration d'une base
  existante. Le mécanisme est au choix de `/develop` (construction concurrente, tâche de fond, hors du sémaphore
  commun…), mais une boîte dont l'index n'existe pas encore **cherche quand même**, par la voie exacte d'aujourd'hui.
- **Coût d'écriture mesuré** : l'index est maintenu à chaque embedding écrit. Le débit d'analyse des messages
  (`enrich`) est le goulet de l'arrivée d'un médecin : sa dégradation est mesurée et consignée.
- **Le stockage est un critère** : `vector` et `halfvec` sont mesurés tous les deux (taille, rappel, temps) ; le choix
  et sa raison sont consignés.
- **Règle 14 inchangée** : l'index vit dans la base de la boîte. Même verdict de l'opérateur, même trace de la
  recherche imputée à la personne réelle.

### Hors périmètre

- La recherche plein texte : task-439. La place des résultats sémantiques dans la réponse : task-440.
- Le corpus et les requêtes de référence de task-438 servent à mesurer le rappel, s'ils sont livrés avant.
- Le calcul ou le modèle des embeddings, et leur écriture : inchangés (seul l'index s'ajoute).
- Le typage de la colonne `Embedding` (dimension fixée) : à rouvrir seulement si l'index sur expression ne suffit pas.
- Aucun client, aucun contrat. Les parcours e2e existants de la recherche sont rejoués par `/e2e`.

## Definition of Done

- [ ] Build passes (0 errors) : `HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) : `HealthPlatform.Api.Mail.sln`
- [ ] **Test d'intégration de bout en bout (règle 1b), `POST /api/v1/Search/semantic`** en mode sémantique, sur la vraie
      pile avec la vraie base du fixture (pgvector), index créé par le chemin réel de provisionnement. Le test vérifie
      que :
      - la réponse réelle rend les messages et documents les plus proches attendus, du bon dossier seulement, dans
        l'ordre attendu, et respecte le seuil de similarité et le nombre maximal de résultats ;
      - le plan de la requête émise passe par l'index (relevé par `EXPLAIN` sur la requête capturée) ;
      - **vu rouge** par mutation (requête rendue à son tri exact d'aujourd'hui, ou index retiré), puis restauré et
        recompilé ; preuve consignée dans le `## Develop log`.
- [ ] **Cas d'échec** : une boîte dont l'index n'existe pas encore rend quand même des résultats, par la voie exacte,
      lus dans la réponse réelle
- [ ] **Plancher de précision** mesuré sur la boîte de 11 178 mails : rappel moyen des 10 premiers résultats contre la
      recherche exacte **≥ 95 %**, sur au moins 20 vraies phrases de recherche ; tableau dans le `## Develop log`
- [ ] **Gain mesuré** sur la boîte de 11 178 mails par `replay.py` (version indexée de la requête) : forme
      vectorielle des contenus de 295,9 ms à **20 ms au plus**, celle des documents de 16,4 ms à **5 ms au plus**,
      plans à l'appui
- [ ] **Construction sans blocage** : test d'intégration où une boîte A s'ouvre pendant la construction de l'index
      d'une boîte B ; l'ouverture de A n'attend pas la fin de la construction de B. Temps de construction et taille de
      l'index consignés pour la boîte de 11 178 mails (`vector` et `halfvec`)
- [ ] Migration auditée (règle 7c) : fichier lu, aucune opération fantôme, `.Designer.cs` présent, aucune dérive ; base
      neuve et base existante toutes deux testées
- [ ] **Débit d'analyse** : escalier `enrich` à 16 médecins, avant / après, dans la même session ; la variation du débit
      en mails par seconde est consignée. Une dégradation de plus de 10 % est posée en question avant `/review`
- [ ] **A/B au banc** (tir court 1400 → 1996, IA simulée, comparé à `bilan-apres` dans la même session) : temps SQL des
      formes vectorielles, p50 / p95 de l'étape « recherche », taille des bases
- [ ] Tests existants de la recherche verts sans modification de leurs assertions
- [ ] Aucune donnée de santé en clair dans les logs (terme de recherche et vecteur compris)
- [ ] **Registre** : FND-010 passe en `task` à la création de ce fichier, puis en `corrigé et mesuré` après la mesure
- [ ] **Prévention (règle d'or)** : une consigne dans `conventions/csharp.md` : une recherche par similarité passe par
      un index et ordonne sur la même expression ; une colonne `vector` sans dimension impose un index sur expression

## Manual Test Plan

1. Lancer le backend sur la boîte de formation de Virginie (11 178 mails) : `cd Api/Mail/src/AppHost && dotnet run`.
   Au premier accès, l'index de la boîte se construit sans bloquer l'ouverture de la boîte.
2. Ouvrir weda2, se connecter avec la CPS de Virginie, ouvrir la boîte de réception.
3. Rechercher « compte rendu de synthèse », « douleur thoracique », « bilan lipidique ».
4. Attendu :
   - les premiers résultats sont ceux d'avant le correctif, à quelques écarts près en fin de liste (comparer avec une
     capture faite sur `develop`) ;
   - dans Seq, la requête `POST /api/v1/Search/semantic` est nettement plus rapide qu'avant.
5. Ouvrir une boîte neuve pendant qu'une autre construit son index : elle s'ouvre sans attendre.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie MSSanté du praticien)
- **Vague Ségur** : hors Ségur — performance interne
- **Exigences DSR honorées** : non applicable — aucune exigence fonctionnelle nouvelle
- **INS** : non applicable — la recherche ne lit ni n'écrit l'INS
- **Authentification PS** : inchangée — PSC (e-CPS), niveau eIDAS substantiel
- **Habilitations** : inchangées — verdict de l'opérateur MSSanté sur la boîte (règle 14)
- **Interop CI-SIS** : non applicable — aucun échange ; les documents déjà analysés sont seulement cherchés
- **Tracé PGSSI-S** : inchangé — la recherche reste tracée au nom de la personne réelle, conservation 3 653 jours
  (`HealthDataAccess`)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — l'index est dérivé des embeddings des messages et documents (données de santé) et vit
  dans la même base de la boîte ; il suit ses sauvegardes et sa suppression
- **AIPD / impact RGPD** : inchangé — aucune donnée nouvelle ; l'index est une structure dérivée, supprimée avec la base
  de la boîte

## Branches
- `api-mail` (pushed) : feat/task-437-recherche-vectorielle-un-index-au-lieu — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-437-recherche-vectorielle-un-index-au-lieu

## Timings

*(généré par `tools/timing/report.sh --task task-437 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 14 s | — | — | — | — |
| /develop | ok | 1 h 12 min | 3 (21 s) | 2 (11 min 01 s) | — | api-mail 3B/2T |
| /sonar | ok | 21 min 22 s | 2 (34 s) | 10 (15 min 32 s) | 4 (1 min 24 s) | 2 itération(s), api-mail 2B/10T |
| /lint-angular | skipped | 0.4 s | — | — | — | client-angular non touché |
| /lint-mobile | skipped | 0.4 s | — | — | — | client-mobile non touché |
| /e2e | ok | 19 min 07 s | — | — | — | e2e ×3 (18 min 41 s) |
| /review | ok | 8 h 20 min | 1 (12 s) | 1 (5 min 33 s) | — | api-mail 1B/1T |
| **Total cycle** | | **10 h 12 min** | **6 (1 min 08 s)** | **13 (32 min 07 s)** | **4 (1 min 24 s)** | |

## Develop log

- **Repos touchés** : api-mail seul. Aucun contrat, aucun client, aucune migration.
- **Commits** : `9b44cbe3` (feature), `de0afa67` (passe qualité).
- **Ce qui change** : la recherche par le sens passe par un **index HNSW** au lieu de calculer la distance de chaque
  message de la boîte.
  - **Index** (`VectorIndexSchema`) : un index par modèle d'embedding actif et par table (`MailContents`,
    `MailMedicalDocuments`).
    - Il est **partiel** sur `"EmbeddingModel" = <modèle>`, en littéral, pour que le planificateur le reconnaisse.
    - Il porte sur l'**expression typée** `("Embedding"::halfvec(D))` : la colonne est un `vector` sans dimension, et
      une boîte peut mêler deux modèles de dimensions différentes.
    - Paramètres : `m = 24`, `ef_construction = 200`.
  - **Construction** : en tâche de fond par le constructeur de task-439 (`SearchTextIndex`), après le texte
    cherchable, au premier usage de la recherche. Mêmes gardes que task-439 :
    - hors du sémaphore de migration ;
    - verrou consultatif ;
    - `lock_timeout` ;
    - deux constructions par processus ;
    - index invalide reconstruit.

    Pas de migration : la boîte s'ouvre sans attendre.
  - **Requête** (`SemanticSearchRepository.SearchByVectorIndexAsync`) :
    - les candidats viennent de l'index (`ORDER BY` sur l'expression indexée, `LIMIT`) ;
    - réglages en `SET LOCAL` dans leur transaction : `hnsw.ef_search = 150`, `hnsw.iterative_scan = relaxed_order`,
      `enable_seqscan = off` ;
    - le dossier est vérifié autour du parcours, dans la même requête (`InFolder` en jointure externe) ;
    - le seuil de distance s'applique ensuite.
  - **Repli exact** :
    - tant que l'index n'est pas prêt : la construction est lancée, jamais attendue ;
    - quand l'index a pu couper un petit dossier (son dernier candidat est encore sous le seuil, et le dossier en a
      gardé moins que demandé) ;
    - sans modèle actif, ou avec un filtre sur le nom du patient : voie d'avant.
  - Une requête d'une autre dimension reste un 409 métier : l'erreur de cast `expected N dimensions` est reconnue.
- **Laboratoire** (`Docs/audits/findings/plans/20261110-vectoriel-task-437/lab_task437.py`) :
  - copie `srch_lab` de la boîte de formation : 11 289 contenus et 563 documents vectorisés, tous en
    `openai:text-embedding-3-small` ;
  - **24 vraies phrases de recherche**, nettoyées par `SearchQueryHelper.BuildCleanedQuery` puis vectorisées comme en
    production ;
  - **rappel@10 contre la recherche exacte**, dossier INBOX, 100 candidats ;
  - médiane de 5 passages.

  | Variante | Contenus : rappel@10 (pire) | Contenus : ms | Documents : rappel@10 (pire) | Documents : ms |
  |---|---|---|---|---|
  | Exacte (avant), balayage | 100 % | 157 ms, 38 312 pages | 100 % | 11,6 ms, 2 524 pages |
  | `vector`, m 16, ef_search 40 (défaut) | 62,5 % (0 %) | 8,5 | — (planificateur : balayage) | 14,3 |
  | `vector`, m 24, efc 200, ef_search 200 | 98,3 % (80 %) | 12,1 | 99,6 % (90 %) | 6,0 |
  | `halfvec`, m 24, efc 200, ef_search 100 | 96,2 % (70 %) | 9,7 | 98,8 % (90 %) | 4,9 |
  | **`halfvec`, m 24, efc 200, ef_search 150 (retenu), forme de production** | **97,9 % (80 %)** | **12,3 ms, 1 986 pages** | **98,8 % (90 %)** | **4,9 ms, 1 365 pages** |

  - **Taille et construction** (contenus / documents) :
    - `vector` : 88 Mo / 4 Mo, en 3,8 s / 0,33 s ;
    - `halfvec` : **44 Mo / 2 Mo**, en 3,3 s / 0,34 s.

    `halfvec` divise par deux le stockage, soit environ 0,45 To au lieu de 0,9 To pour 10 000 médecins, pour moins
    d'un point de rappel.
  - **Ce que la mesure a appris** :
    - le réglage par défaut rate les vrais voisins des phrases courtes (rappel nul sur 6 phrases) ;
    - le planificateur bascule entre index et balayage d'une valeur d'`ef_search` à l'autre ;
    - un filtre de dossier dans le parcours (`EXISTS` réordonné, sous-requête, `= ANY`) lui fait quitter l'index.

    D'où les choix retenus : `enable_seqscan` désactivé localement et le dossier vérifié autour du parcours.
  - **Distance en demi-précision** dans la réponse (écart de l'ordre du millième) : relire le vecteur entier coûtait
    une milliseconde de plus sur les documents (5,8 ms au lieu de 4,9).
- **DoD — plancher et gain** :
  - rappel moyen 97,9 % (contenus) et 98,8 % (documents), plancher de 95 % ✓ ;
  - contenus 157 → 12,3 ms (objectif ≤ 20) ✓ ;
  - documents 11,6 → 4,9 ms (objectif ≤ 5) ✓ ;
  - baseline de la task (code `405da376`) : 296 / 16,4 ms. Sur `develop` d'aujourd'hui, la voie exacte mesure
    157 / 11,6 ms.
- **Règle 1b — tests d'intégration de bout en bout** (`POST /api/v1/Search/semantic`, mode sémantique, vraie pile,
  PostgreSQL et pgvector, index construit par le chemin réel) — `SearchVectorIndexIntegrationTests` :
  - les plus proches du dossier courant, contenus et documents mêlés, dans l'ordre, sous le seuil, dans la limite. Le
    plan de la requête émise (`EXPLAIN`, mêmes réglages) cite l'index des deux tables ;
  - **cas d'échec** : une boîte sans index (un autre processus tient la construction) répond quand même, par la voie
    exacte ;
  - un petit dossier d'une grande boîte n'est pas perdu derrière la boîte de réception (repli exact) ;
  - **construction sans blocage** : une lecture tient la boîte B, A cherche et répond en moins de 15 s, puis l'index de
    B se construit.
- **Vu rouge par mutation**, restaurée puis recompilée (`--no-incremental`), rejouée après la passe qualité :

  | Mutation | Test au rouge |
  |---|---|
  | M1 — requête ordonnée sur la distance exacte (`"Embedding" <=> q`), pas sur l'expression indexée | le plan ne passe plus par l'index |
  | M2 — construction de l'index retirée | idem |
  | M3 — repli exact retiré | le message du petit dossier est perdu |

- **Tests unitaires** : `VectorIndexSchemaTests` (8) :
  - modèles indexables ou non (dimension 0, > 4 000) ;
  - nom d'index stable par modèle ;
  - littéral échappé ;
  - index et requête sur la même expression ;
  - réglages locaux à la transaction.
- **Tests existants de la recherche** : verts sans modification de leurs assertions (279). Dont les modèles à 3 et 5
  dimensions de task-325, qui passent désormais par le chemin indexé.
- **Passe qualité (/simplify)**, 2 relectures :
  - Appliqué :
    - réponse exacte immédiate tant que l'index n'est pas prêt (avant, la recherche pouvait balayer deux fois) ;
    - dossier vérifié dans la même requête que les candidats (un aller-retour de moins par table) ;
    - un seul état « prêt » et une seule vérification au catalogue ;
    - SQL de suppression d'un index invalide partagé ;
    - transaction simplifiée ;
    - une condition et une aide de construction uniques ;
    - côté tests, un seul générateur d'embeddings et une seule aide de verrou.
  - Écarté :
    - `SET LOCAL` dans la même commande : EF enveloppe la requête composée dans une sous-requête ;
    - une requête commune aux deux tables : il faudrait changer l'interface du dépôt ;
    - renommer `SearchTextIndex` : trop de changements autour du code de task-439.
- **Build et tests locaux** : `HealthPlatform.Api.Mail.sln` sans erreur ni avertissement. Tests : domain 210,
  infrastructure 737, api 1 375, application 4 054, intégration 1 232 (+ 16 écartés), 0 échec.
- **Aucune donnée de santé dans les journaux** : deux messages nouveaux (« Vector index of {Database} built »), sans
  terme ni vecteur.
- **Registre** : FND-010 porte la mesure d'après (laboratoire). Le statut passe en « corrigé et mesuré » au merge,
  selon la définition du registre (task mergée).
- **Prévention (règle d'or)** : `conventions/csharp.md`, entrée `recherche-par-similarite-indexee`.
- **DoD — restent à faire, avec le banc de charge (à décider avec l'humain)** :
  - escalier `enrich` à 16 médecins, avant / après, pour le coût d'écriture de l'index ;
  - A/B du tir court 1400 → 1996.
- Next step : /sonar task-437

## Sonar log

**Mode A** (chaîné depuis `/develop`), `api-mail`, branche `feat/task-437-…`, 2 analyses (build `Release`).

### KPIs qualité (baseline → final)

| KPI | Baseline (analyse de task-440) | Itération 1 | Final |
|---|---|---|---|
| Quality Gate | OK | OK | **OK** |
| Bugs / Vulnérabilités | 0 / 0 | 0 / 0 | 0 / 0 |
| Code smells | 0 | 3 | **0** |
| Hotspots à revoir | 0 | 0 | 0 |
| Couverture globale | 97,8 % | 97,8 % | **97,8 %** |
| Couverture du nouveau code | 96,0 % | 96,0 % | **96,0 %** |
| Duplication | 0,4 % | 0,4 % | 0,4 % |

**Phase 1 — nouveau code** : 3 issues, toutes corrigées (`911aea4d`) :
- deux `S107` (8 et 9 paramètres) : les paramètres de la recherche vectorielle sont regroupés dans un enregistrement
  `VectorQuery` ;
- un `CA1822` : `NearestByIndexAsync` devient statique.

Les 283 tests de la recherche sont verts après la correction.

**Phase 2 — dette ancienne** : 0 issue ouverte.

**Tests de l'analyse** : domain 210, application 4 054, infrastructure 729 + 8, api 1 375, intégration 1 229 + 3 rouges.
Les 3 rouges sont les tests « du jour » (`FilterTodayEmails…`, `GetFolderTodayAsync…`, `GetFolderNotSeenTodayAsync…`),
joués à 0 h 05 et 0 h 15, dans la fenêtre connue de minuit à 1 h (la recherche IMAP `SINCE` compare en UTC). Ils sont
étrangers à la task et rejoués isolés après 1 h (voir ci-dessous).

**Conventions** : `S107` corrigé à la main sur du code neuf. L'entrée `S107` de `conventions/csharp.md` (qui ne
visait que les `[LoggerMessage]`) est complétée, cas « méthode de dépôt », et passe à 2 occurrences.

## Lint log

- `/lint-angular` : skip — client-angular non touché par la task.
- `/lint-mobile` : skip — client-mobile non touché par la task.

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail touché | ✅ verte | 60 verts, 0 flaky, 0 rouge, 0 quarantaine | 9 min 04 s |
| angular | api-mail touché | ✅ verte | 73 verts, 0 flaky, 0 rouge, 1 quarantaine (E2E-COMPOSE-002, verte) | 9 min 37 s |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ branche de la task (`feat/task-437-…`), inchangé par la task
- Quarantaines : [angular] E2E-COMPOSE-002, correction task-350 (posée par l'humain, verte à ce passage)
- Divergences ouvertes : aucune
- Parcours touchés sans spec e2e modifié : aucun écran touché (task backend)
- Démontage : complet (ports libres, aucun conteneur e2e résiduel)

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
| E2E-SEARCH-002 | 1 | headless | Un mot rare et accentué trouve le message qui le contient | ✅ | ✅ |
| E2E-SEARCH-003 | 1 | headless | Un numéro de dossier trouve son message, et un seul | ✅ | ✅ |
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

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/357 — label `awaiting-human-merge`

**Avant le merge** (décision humaine du 2026-11-11) : escalier `enrich` à 16 médecins avant / après, et A/B du tir
court 1400 → 1996. Une dégradation de l'analyse de plus de 10 % se pose en question.

## Code Review Summary

**APPROVED — 0 bloquant, 4 suggestions.** Build et tests verts (7 608 tests, 0 échec ; les 3 tests « du jour »,
rouges entre minuit et 1 h, sont rejoués verts à 8 h 55), Quality Gate OK (3 issues du nouveau code corrigées),
`## E2E log` vert.

- **Règle 1b** (`SearchVectorIndexIntegrationTests`, endpoint réel, index construit par le chemin réel) :
  - plus proches du dossier courant, contenus et documents, dans l'ordre, sous le seuil, dans la limite, et requête qui
    passe par l'index (`EXPLAIN`) → rouges sous M1 (tri sur la distance exacte) et M2 (construction retirée) ;
  - boîte sans index → réponse exacte (cas d'échec, lu dans la réponse) ;
  - petit dossier d'une grande boîte → rouge sous M3 (repli retiré) ;
  - construction sans blocage d'une autre boîte (A répond en moins de 15 s).
- **Sécurité** : littéral du modèle échappé, noms de table internes, dimension entière ; aucun terme ni vecteur dans les
  journaux.
- **DoD** : plancher de précision (97,9 % / 98,8 %) et gain (12,3 ms / 4,9 ms) mesurés au laboratoire ; migration sans
  objet ; registre à passer en « corrigé et mesuré » au merge ; deux mesures de banc à faire avant le merge.
- **Suggestions** :
  1. resserrer la reconnaissance du conflit de dimension (exiger « dimensions ») ;
  2. distance en demi-précision côté index, pleine côté exact (≈ 10⁻³, effet possible pile au seuil) ;
  3. coût d'écriture de l'index sur `enrich`, à mesurer au banc ;
  4. stockage : environ 0,45 To d'index pour 10 000 médecins.
