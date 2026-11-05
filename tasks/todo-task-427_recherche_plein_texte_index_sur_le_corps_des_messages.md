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
