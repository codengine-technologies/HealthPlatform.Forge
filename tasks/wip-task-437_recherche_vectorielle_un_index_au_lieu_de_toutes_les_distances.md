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
| **Total cycle** | | **14 s** | **0 (0.0 s)** | **0 (0.0 s)** | **0 (0.0 s)** | |
