# todo-task-427.md — La recherche du médecin ne relit plus tous ses messages : un index sert la recherche dans le texte

**Repos**: api-mail
**Dependencies**: — (aucune ; indépendante de task-426)
**Epic**: E015
**Single frontend**: true
**Priorité**: **3**.
- La recherche reste dans sa cible de p95 à 1996 médecins actifs, mais sa médiane en sort de peu (532 ms pour 500).
- Elle pèse la **moitié du temps de calcul de Postgres** : c'est la plus grosse marge disponible sur la base.
- Le correctif touche le schéma de chaque base praticien : il se décide sur mesure, sans urgence.

> **Origine.** Tir court 1400 → 1996 médecins actifs du 2026-11-05 (task-422, IA simulée, pool PgBouncer à 1), finding
> **F1**. Rapport et analyse : `Docs/audits/api-mail-loadtest-journey-courte-1400-1996-task422-20261105.md`, section
> « Findings d'optimisation ».

## Ce qui est établi

| Forme `pg_stat_statements` | Appels sur 39 min | ms par appel | Blocs de 8 Ko par appel | Part du temps SQL |
|---|---|---|---|---|
| `SELECT … FROM "MailContents" … WHERE m."Body" ILIKE $2 … ORDER BY SentDate DESC … LIMIT $3` | 46 074 | 16,0 | 269 | **25,9 %** |
| `SELECT … FROM "MailMedicalDocuments" … WHERE m."Body" ILIKE $2 … LIMIT $3` | 46 083 | 15,2 | 314 | **24,7 %** |

- **Émises par** `SemanticSearchRepository.ExecuteFullTextSearchAsync`. Pour chacun des 3 premiers termes de la
  saisie, une requête `ILIKE '%terme%'` par table, à la suite : jusqu'à **6 requêtes par recherche**. Environ
  15 000 recherches dans le tir, soit environ 3 termes par recherche.
- **Aucun index ne sert un `ILIKE` à joker initial.** Chaque appel relit les corps du dossier, d'où 2 à 2,5 Mo touchés
  par appel.
- **Côté médecin**, c'est l'étape 5 « Recherche » : p50 532 ms (cible 500) et p95 992 ms (cible 2 000) à 1996 actifs.
  La part sémantique (embeddings) du même appel n'est pas concernée.
- **Contrainte forte** : la mémoire Postgres est la **prochaine limite** mesurée (conteneur à 100 % de 48 Go, taux de
  cache 96,7 %). Un index qui coûte plus de mémoire qu'il n'en fait gagner en lectures serait une mauvaise affaire.

## Objective

Une recherche ne relit plus tous les corps de messages du dossier : un index la sert. **Les résultats de la recherche
restent exactement les mêmes qu'aujourd'hui.**

**Décision produit (PO, 2026-11-05) : la sémantique ne change pas.** Le médecin retrouve un message dès que son texte
contient la suite de caractères tapée, sans tenir compte de la casse, comme aujourd'hui. Cela exclut une recherche
« plein texte » linguistique (`tsvector`) : elle changerait ce qui est trouvé (racines, mots vides, découpage). Si elle
est souhaitée un jour, ce sera une US à part, avec ses propres critères de pertinence.

Contenu attendu :
1. **Mesurer d'abord.** `EXPLAIN (ANALYZE, BUFFERS)` des deux formes sur la base praticien la plus remplie du banc :
   - sans index ;
   - avec un index GIN `pg_trgm` (`gin_trgm_ops`) sur `MailContents.Body` et `MailMedicalDocuments.Body` ;
   - avec les termes regroupés en une seule requête par table (`ILIKE ANY`).

   Relever durée, blocs touchés, taille des index face à la taille des corps, et durée de construction. Le tout est
   consigné dans le task file **avant** d'écrire la migration.
2. **Retenir ce que la mesure justifie.** Index trigramme, regroupement des requêtes, ou les deux. Si l'index coûte
   plus qu'il ne rapporte (taille, mémoire, écriture des messages enrichis), on garde le seul regroupement et le task
   file dit pourquoi.
3. **Migration EF** (si index retenu) : extension `pg_trgm` et index, appliqués à chaque base praticien par le chemin
   de création et de mise à jour existant. La durée de construction sur une grosse boîte est mesurée et indiquée pour
   la mise en production.

### Hors périmètre

- La recherche sémantique (embeddings, pgvector) : inchangée.
- Le cache du registre : task-426.
- Aucun client, aucun contrat.

## Definition of Done

- [ ] Build passes (0 errors) : `HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) : `HealthPlatform.Api.Mail.sln`
- [ ] Mesure préalable consignée dans le task file **avant** le code : plans `EXPLAIN (ANALYZE, BUFFERS)` des variantes,
      taille des index, durée de construction, sur une base praticien du banc. Variante retenue et raison
- [ ] **Résultats inchangés, test d'intégration de bout en bout (règle 1b)** sur la route de recherche, à travers la
      vraie pile jusqu'à la vraie base : mêmes messages trouvés qu'avant pour
      - un terme dans le corps d'un message ;
      - un terme dans le corps d'un document médical ;
      - une casse différente ;
      - un terme contenant `%` ou `_` (échappement, task-192) ;
      - plusieurs termes ;
      - un terme absent.

      Les tests existants de task-192 (dédoublonnage, troncature, `Hits`, `IsTruncated`) restent verts sans
      modification de leurs assertions
- [ ] Si regroupement des termes : vu rouge par mutation (un terme ignoré dans la requête groupée → le test échoue)
- [ ] Si migration : audit règle 7c (fichier relu, aucune opération fantôme, `.Designer.cs` et snapshot présents,
      `has-pending-model-changes` à vide). L'extension `pg_trgm` est créée par la migration, et une base neuve comme une
      base existante la reçoivent
- [ ] **Mesure au banc** (skill `loadtest-skill`, même tir court que task-422 : `JOURNEY_STAGES="1400:18m,1996:18m"`,
      IA simulée, pool 1) :
      - temps SQL des formes de recherche **−50 % au moins** ;
      - étape « Recherche » dans sa cible de p50 (500 ms) à 1996 ;
      - `EnrichPersistMail` (écriture d'un message enrichi) : p95 dégradé de **20 % au plus** ;
      - aucun autre p95 d'étape dégradé de plus de 20 % ;
      - taux de cache Postgres pas plus mauvais qu'au tir de référence ;
      - 0 erreur 5xx en régime
- [ ] Taille totale des index ajoutés sur les 2 000 bases du banc, et extrapolation à 10 000 boîtes, écrites dans le task
      file pour le dimensionnement de production
- [ ] Aucune donnée de santé dans les journaux ajoutés, ni dans le task file : les plans et mesures portent sur des
      données synthétiques, sans terme de recherche réel

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost`, profil par défaut, une boîte rattachée avec des messages et des
   comptes rendus.
2. Dans le client (`client-blazor` ou `client-mobile`), rechercher un mot présent dans le texte d'un message : le message
   est trouvé.
3. Rechercher le même mot en majuscules : mêmes résultats.
4. Rechercher un mot présent seulement dans un compte rendu joint : le message porteur est trouvé.
5. Rechercher deux mots, puis un mot absent : résultats cohérents, aucun message en trop.
6. Rechercher `50%` : aucune erreur, résultats limités aux messages qui contiennent `50%`.
7. Au banc (facultatif) : rejouer le tir court et comparer le temps SQL de la recherche.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur. Performance interne
- **Exigences DSR honorées** : non applicable. Ce que le PS trouve en recherchant est strictement inchangé
- **INS** : non applicable. Aucun trait d'identité patient n'est manipulé
- **Authentification PS** : inchangée (PSC / e-CPS)
- **Habilitations** : inchangées (règle 14). L'index vit dans la base de la boîte, qui reste la seule base des données
  de santé de la boîte. Aucune copie, aucune base par personne
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé. La recherche reste imputée à son auteur comme aujourd'hui
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui, environnement inchangé. L'index est une structure dérivée du corps des messages, dans
  la même base HDS et sous le même chiffrement au repos
- **AIPD / impact RGPD** : à noter : l'index trigramme est une donnée dérivée du contenu des messages. Il est
  supprimé avec la base de la boîte et ne crée aucun traitement nouveau

## Mesure préalable (2026-11-05, avant le code)

Base praticien la plus volumineuse du banc (`u_l9l_b27c…`, 156 messages, dossier INBOX), données synthétiques. Saisie
du tir : « compte rendu de synthese », soit 3 termes. `EXPLAIN (ANALYZE, BUFFERS)`.

| Variante | `MailContents` | `MailMedicalDocuments` | Recherche entière (2 tables) |
|---|---|---|---|
| **Actuelle** : 1 `ILIKE '%terme%'` par terme et par table | 8,2 + 8,9 + 8,3 ms | 7,3 + 7,3 + 7,4 ms | **≈ 47 ms**, 6 requêtes |
| Index GIN `pg_trgm` sur `Body` (2 index) | **ignoré par le planificateur** : 9,2 ms, balayage séquentiel | idem | ≈ 47 ms |
| … même index, balayage séquentiel interdit (`enable_seqscan=off`) | 2,4 ms pour un terme fréquent, 9,1 ms pour un terme absent | — | non atteignable sans forcer |
| Termes regroupés : `ILIKE ANY` ou 3 `ILIKE` en un passage | 19,9 / 26,4 ms | — | pas de gain : chaque `ILIKE` refait le travail |
| Expression régulière `~* '(t1\|t2\|t3)'` | 8,3 ms | 8,8 ms | n'identifie pas le terme ; sémantique différente |
| **Retenue** : corps mis en minuscules **une fois** (CTE `MATERIALIZED`), puis `LIKE lower(motif)` par terme, tri et limite par terme en SQL, corps des candidats rendus | **10,9 ms** | **10,1 ms** | **≈ 21 ms, −55 %**, 2 requêtes |

**Ce qui coûte.** Ce n'est pas l'absence d'index, c'est la **mise en minuscules du corps entier**, refaite à chaque
`ILIKE`. `lower(Body)` seul coûte 9,3 ms sur la table, `ILIKE` 8,0 ms. Dans une base UTF-8, PostgreSQL exécute
`a ILIKE p` comme `lower(a) LIKE lower(p)` (`like.c`, `Generic_Text_IC_like`). Calculer `lower(Body)` une fois et
comparer les termes au résultat donne donc **exactement les mêmes correspondances**.

**Index trigramme écarté.**
- 1,3 Mo pour `MailContents` et 1,4 Mo pour `MailMedicalDocuments` sur cette base, soit environ 3 fois la taille
  compressée des corps (433 et 380 Ko). Construction : 115 et 102 ms.
- Extrapolation : environ 5,4 Go sur les 2 000 bases du banc, et environ 27 Go pour 10 000 boîtes **à volume égal**,
  davantage avec des boîtes réelles plus grosses.
- Le planificateur ne s'en sert pas, faute de compter le coût de décompression des corps.
- Il coûte de la mémoire, qui est précisément la prochaine limite mesurée (task-422).
- **Aucune migration, aucune extension.**

**Conception retenue.**
- **Phase 1 (EF, inchangée)** : la requête de base garde ses règles (dossier, dossier-étiquette `InFolder`, patient).
  Elle ne rend que les identifiants des lignes candidates, sans leur corps.
- **Phase 2 (SQL)** : une requête par table.
  - CTE `MATERIALIZED` : `lower(Body)` une seule fois, sur les lignes de la phase 1.
  - Jointure avec les motifs (`unnest … WITH ORDINALITY`, `LIKE lower(motif) ESCAPE ''`).
  - `row_number()` par terme dans l'ordre actuel (`SentDate IS NULL`, `SentDate DESC`, `Uid DESC`), limite de 200 par
    terme.
  - Corps des seules lignes retenues.
- **En mémoire, inchangé** : candidats dans l'ordre terme puis date, dédoublonnage par message, filtre `Contains`,
  score, tri, limite.

## Develop log

- **Variante retenue** : mise en minuscules unique, sans index ni migration (voir « Mesure préalable »). L'audit de
  migration (règle 7c) est sans objet.
- **Code** (`api-mail`, `src/Infrastructure/Repositories/MailDb/SemanticSearchRepository.cs`) :
  - les trois recherches plein texte (contenus, documents médicaux, documents d'un patient) gardent leur requête EF
    de base, qui porte les règles de dossier, de dossier-étiquette (`InFolder`) et de patient, mais n'en lisent plus
    que les identifiants de lignes ;
  - une requête SQL par table (`SqlQueryRaw<TermHit>`, constantes de compilation) :
    - chaque corps est mis en minuscules **une fois**, dans une sous-requête latérale non inlinée (`OFFSET 0`) ;
    - les termes sont comparés au résultat (`LIKE lower(motif) ESCAPE`, caractère tiré de
      `SearchQueryHelper.LikeEscapeCharacter`) ;
    - classement `row_number()` par terme dans l'ordre de task-192, limite de 200 par terme ;
    - `DISTINCT ON` ligne, sur son premier terme, avec son corps ;
  - en mémoire, inchangé : ordre terme puis rang, dédoublonnage par message, filtre `Contains`, score, tri, limite.
- **Passe qualité §Q** (`/simplify`, 4 relectures) :
  - **appliqué** :
    - CTE `MATERIALIZED` remplacée par la sous-requête latérale en flux : même coût mesuré (10,8 ms contre
      10,9 ms), et plus de copie en minuscules du dossier stockée, donc plus de risque de débordement sur disque
      au-delà de `work_mem` pour un gros dossier ;
    - `DISTINCT ON` au lieu d'une seconde fenêtre et d'un `CASE` ;
    - phase 1 réduite aux identifiants : suppression de `CandidateRow` et de sa table de correspondance ;
    - échappement tiré de `LikeEscape` au lieu d'être écrit en dur ;
    - `Body IS NOT NULL` redondant retiré ;
    - `SearchMode.FullTextOnly` dans le test.
  - **écarté** : recopier en SQL la règle des dossiers-étiquettes pour supprimer l'aller-retour des identifiants.
    Une règle métier en double coûte plus qu'une liste d'identifiants (16 octets par ligne).
- **Tests d'intégration, règle 1b** (`tests/mss.mail.integration.tests/Api/FullTextSearchSinglePassIntegrationTests.cs`,
  9 tests, route `POST /api/v1/search/semantic` et `/search/patient`, vraie pile jusqu'à PostgreSQL) :
  - **verts sur l'ancien code et sur le nouveau** : le comportement est identique ;
  - cas couverts : terme dans le corps d'un message, terme dans un document médical, casse et accents, `%` et `_`
    littéraux, fenêtre saturée de faux candidats, ordre des plus récents dans une fenêtre pleine, plusieurs termes et
    ordre du score, terme absent, document d'un autre patient.
- **Preuve par mutation**, jouée sur la version finale, chaque mutation réinjectée puis restaurée par réécriture :

  | Mutation | Test qui échoue |
  |---|---|
  | M1, un seul terme envoyé | `Semantic_SeveralTerms_…` |
  | M2, corps non mis en minuscules | 7 tests, dont `Semantic_TermInUpperCaseWithAccents_…` |
  | M3, motif non échappé | `Semantic_WildcardLookalikesFillingTheWindow_…` (ajouté après que M3 a d'abord survécu : le filtre `Contains` masque le défaut tant que la fenêtre n'est pas pleine) |
  | M4, filtre de base ignoré | `Patient_TermInAnotherPatientsDocument_IsNotFound` |
  | M5, ordre de date inversé | `Semantic_MoreMatchesThanTheWindow_KeepsTheMostRecentMails` |
- **Validation** (après la passe qualité, recompilée) : build 0 erreur et 0 avertissement. Tests : domain 202,
  infrastructure 700, application 4 003, api 1 357, intégration 1 114 (+16 ignorés), **0 échec**.
- **Incident de méthode, corrigé.** Un premier passage de la suite complète, après les mutations, a rendu 3 échecs
  (ordre des dates). Il tournait en `--no-build` sur les binaires de la dernière mutation (M5) : le script restaurait
  le source sans recompiler. Le commit de la passe qualité, enchaîné dans la même commande que la lecture du
  résultat, est parti avant que ces échecs soient lus. Le source poussé était bien le bon (vérifié, aucune trace de
  la mutation), et la suite recompilée est verte. Prévention : le script recompile après restauration, et la
  mémoire de session est mise à jour (lire, puis committer, jamais dans la même commande).

## Mesure au banc (2026-11-05, 23:13 → 23:51)

Même tir court que la référence de task-422 : `JOURNEY_STAGES="1400:18m,1996:18m"`, K = 1, IA simulée, pool
PgBouncer à 1, mêmes bases, même tireur, `LATENCY_MS=96`. Proxies Toxiproxy présents à chaque contrôle (toutes les
30 s). Seule différence de code : la branche task-427.
- Référence : `Docs/audits/api-mail-loadtest-journey-courte-1400-1996-task422-20261105.md`.
- Ce tir : `Docs/audits/api-mail-loadtest-journey-courte-1400-1996-task427-20261106.md`.

| Critère de la DoD | Référence (task-422) | task-427 | Tenu |
|---|---|---|---|
| Temps SQL des formes de recherche (`pg_stat_statements`) | 23,9 min, 92 157 appels (50,6 % du SQL) | **5,1 min**, 16 525 appels (20,9 %) | ✅ **−79 %** (cible −50 %) |
| Recherche, p50 à 1996 (cible 500 ms) | 532 ms | **384 ms** | ✅ |
| `EnrichPersistMail`, p95 | 453 ms | 425 ms | ✅ (mieux) |
| Pire écart de p95 d'étape, 1400 et 1996 | — | aucune étape dégradée, toutes améliorées | ✅ |
| 5xx en régime | 0 | 0 (erreurs 0,00 % et 0,01 %, réseau du relais) | ✅ |
| Taux de cache Postgres | 96,74 % | 96,34 % | ⚠️ voir ci-dessous |

**Taux de cache : critère non tenu à la lettre, tenu sur le fond.**
- Le taux baisse de 0,4 point, mais les **lectures disque sont inchangées** : 2 006 703 blocs avant, 1 992 204 après.
- Ce sont les lectures servies par le cache qui chutent (115,8 → 95,7 millions de blocs), parce que la recherche ne
  relit plus six fois les corps.
- Le ratio baisse donc par son dénominateur, pas par un débordement de la mémoire.
- Le critère visait à interdire un index qui chasserait du cache le jeu de travail. Aucun index n'a été ajouté.

> **Arbitrage humain (2026-11-06)** : critère **accepté sur son intention** (réponse « 1 » à `questions/task-427.md`) : les lectures disque ne sont pas accrues, aucun index n'a été ajouté. Le point figure en tête du corps de la PR.

**Effets mesurés au-delà de la recherche**, p95 à 1996 :

| Étape | Avant | Après |
|---|---|---|
| Dashboard | 678 ms | 579 ms |
| Inbox | 356 ms | 202 ms |
| Message servi base | 318 ms | 170 ms |
| Recherche | 992 ms | 704 ms |
| Fiche patient | 2 034 ms | 1 119 ms |

Autres effets :
- **Temps SQL total du tir** : 47,3 → 24,6 min, soit 3,8 → 2,0 ms de SQL par requête HTTP.
- **Postgres** : 1,79 backend actif équivalent au lieu de 2,49.
- **Fautes majeures du cgroup Postgres** : au plus 0,6/s au lieu de 22,3/s.

La moitié du temps de Postgres libérée profite à toutes les étapes servies par la base.

**Index : rien à dimensionner pour la production.** Aucun index n'a été ajouté. L'extrapolation de l'index écarté
figure dans « Mesure préalable » (environ 27 Go pour 10 000 boîtes à volume égal).

## Sonar log

- **Mode A (chaîné)**, `api-mail` sur `feat/task-427-recherche-plein-texte-index-sur-le-corps`.
- **Itération 1** : 11 issues sur le nouveau code, toutes sur `SemanticSearchRepository.TermHit`. C'est une classe
  privée `{ get; init; }` matérialisée par `SqlQueryRaw<T>`, que Sonar ne voit pas affectée : ×5 `S3459` et ×6
  `S1144`, dont `RowId`, réellement inutilisé côté C#.
- **Correction** : `TermHit` passe en `record` positionnel (EF lie le constructeur) et `RowId` est retiré du `SELECT`
  et du type (`da6b30dd`, commit `refactor(search): S1144/S3459`). Les 189 tests de recherche restent verts.
- **Récidive** de la consigne « S3459-S1144 — un DTO de désérialisation privé s'écrit en `record` positionnel »
  (`conventions/csharp.md`, occurrences 1 → 2). Cause : la lecture du fichier s'était arrêtée aux 40 premiers titres.
- **Itération 2** : 0 issue sur le nouveau code, Quality Gate OK, 0 hotspot.
  - Les requêtes SQL brutes sont des constantes de compilation : pas de S2077.
- **Tests sous couverture** : 3 échecs à chaque passage, toujours les mêmes, les tests « du jour » rouges connus
  entre 00:00 et 02:00 (IMAP `SINCE` en UTC) :
  - `EmailReadingUseCaseTests.FilterTodayEmailsShouldReturnOnlyTodayAsyncAsync` ;
  - `ImapFolderServiceIntegrationTests.GetFolderTodayAsync_…` ;
  - `ImapFolderServiceIntegrationTests.GetFolderNotSeenTodayAsync_…`.

  Les deux analyses ont tourné vers minuit. Ces tests sont sans lien avec la recherche, et seront rejoués après
  02:00.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | = |
| Issues new code | 0 (puis 11 au 1er scan de la branche) | 0 | = |
| New coverage | 96,0 % | 96,0 % | = |
| Bugs / Vulnérabilités / Code smells | 0 / 0 / 0 | 0 / 0 / 0 | = |
| Security hotspots | 0 | 0 | = |
| Coverage projet | 97,8 % | 97,8 % | = |
| Duplication | 0,4 % | 0,4 % | = |
| Ratings fiabilité / sécurité / maintenabilité | A / A / A | A / A / A | = |

## Lint log

- `/lint-angular` : **skipped** — `client-angular` n'est pas dans les `**Repos**` de la task.
- `/lint-mobile` : **skipped** — `client-mobile` n'est pas dans les `**Repos**` de la task.

## E2E log

| Voie | Déclenchée par | Résultat |
|---|---|---|
| mobile (`npm run e2e:headless`) | `api-mail` touché | ✅ 58 verts, 0 flaky, 0 rouge, parité verte |
| angular (`npm run e2e:mss`) | `api-mail` touché | ✅ 71 verts, 0 flaky, 0 rouge, parité verte (port 47399 vérifié libre avant la voie) |

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

- E2E-SEARCH-001 (« Rechercher un message et ouvrir la recherche avancée ») vert sur les deux clients.
- Démontage vérifié : ports e2e libres, aucun conteneur laissé par ce run. Les deux conteneurs anciens
  `e2e-greenmail-gcgjbrzp` et `e2e-dovecot-kgrndjwd` (arrêtés depuis le 2026-10-14) sont toujours là.

## Branches

- `api-mail` (pushed) : feat/task-427-recherche-plein-texte-index-sur-le-corps — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-427-recherche-plein-texte-index-sur-le-corps
  - Créée depuis `origin/develop` (`d6712a10`).

## Timings

*(généré par `tools/timing/report.sh --task task-427 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 17 s | — | — | — | — |
| /develop | ok | 1 h 25 min | 5 (48 s) | 5 (17 min 04 s) | — | api-mail 5B/5T, variante sans index ; banc : SQL recherche -79 % |
| /sonar | ok | 23 min 57 s | 3 (1 min 29 s) | 12 (14 min 07 s) | 4 (1 min 19 s) | 2 itération(s), api-mail 3B/12T |
| /lint-angular | skipped | 0.4 s | — | — | — | repo non listé dans Repos |
| /lint-mobile | skipped | 0.4 s | — | — | — | repo non listé dans Repos |
| /e2e | ok | 19 min 13 s | — | — | — | e2e ×5 (37 min 29 s) |
| /review | ok | 1 min 17 s | 1 (8.9 s) | 1 (5 min 20 s) | — | api-mail 1B/1T, PR #342, arbitrage cache accepté (option 1), validation réutilisée à da6b30dd |
| **Total cycle** | | **2 h 10 min** | **9 (2 min 26 s)** | **18 (36 min 32 s)** | **4 (1 min 19 s)** | |

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/342 — label `awaiting-human-merge`
  (critère « taux de cache » accepté sur arbitrage humain du 2026-11-06, en tête du corps de la PR).

## Code Review Summary

**APPROVED** — 2 fichiers revus, 0 point bloquant, 2 suggestions.

- Build : 0 erreur. Tests : 0 échec (validation de `/review` à da6b30dd, branche inchangée depuis, à jour avec
  `develop` ; les 3 tests « du jour » rejoués verts à 02:02).
- DoD : tous les critères tenus ; « taux de cache » accepté sur son intention par l'humain (lectures disque non
  accrues) ; migration et audit 7c sans objet (aucun index) ; dimensionnement : rien à ajouter en production.
- **Règle 1b — comportement → test → preuve rouge** (`FullTextSearchSinglePassIntegrationTests`, routes
  `/search/semantic` et `/search/patient`, vraie pile jusqu'à PostgreSQL) : tous les termes (M1), casse (M2), `%`/`_`
  littéraux (M3), filtre patient (M4), fenêtre des plus récents (M5). Détail dans le `## Develop log`.
- Sécurité : SQL constant de compilation, entièrement paramétré ; aucune donnée de santé dans les journaux.
- Suggestions non bloquantes : identifiants candidats transitant par l'application (choix assumé, règle des
  dossiers-étiquettes non dupliquée en SQL) ; filtre `Contains` en mémoire qui double le `LIKE` SQL, gardé pour la
  sémantique identique.
