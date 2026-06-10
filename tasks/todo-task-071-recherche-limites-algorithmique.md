# todo-task-071.md — Perf recherche : bornage des requêtes full-text et corrections algorithmiques

**Repos**: api-mail
**Dependencies**: (aucune)
**Epic**: E011

> US mono-repo justifiée : optimisation backend pure de la recherche
> (full-text + sémantique). Mêmes résultats fonctionnels, mêmes contrats.

## Objective

Borner les requêtes de recherche full-text qui chargent aujourd'hui un volume
non limité de mails en mémoire (potentiellement toute la boîte) avant de
filtrer côté client, et corriger les anti-patterns algorithmiques du chemin de
recherche (intersections O(N×M), allocations inutiles dans les logs).

## Findings adressés (audit perf 2026-06-10)

| # | Localisation | Problème | Impact |
|---|---|---|---|
| 1 | `src/Infrastructure/Repository/SemanticSearchRepository.cs:494-517` | `ExecuteFullTextSearchAsync` : 3 requêtes `ILike '%term%'` **sans `Take`**, puis `GroupBy`/`Where`/`Select` entièrement en mémoire sur un volume non borné | Élevé |
| 2 | `src/Infrastructure/Repository/SemanticSearchRepository.cs:55,96,116,290,297,303,309,319` | `queryVector.ToArray().Length` dans les logs : allocation d'un `float[]` complet juste pour la longueur, à chaque recherche | Moyen |
| 3 | `src/Application/Services/Implementation/SemanticSearchService.cs:93-94` | `Where(r => filteredUids.Contains(r.Uid))` avec `List` = O(N×M) → HashSet | Moyen |
| 4 | `src/Infrastructure/Repository/PatientRepository.cs:137-142` | Liste de `patientIds` du jour chargée sans limite | Moyen |

## Comportement attendu

- Chaque requête full-text est bornée (`Take` par terme + borne sur le résultat
  final) avec un plafond configurable ; le filtrage/dédoublonnage redescend en
  SQL quand c'est traduisible, sinon opère sur un volume borné.
- À volume égal, les résultats restent fonctionnellement identiques pour
  l'utilisateur (mêmes top-résultats, même ranking) — toute divergence de
  ranking doit être documentée dans la PR.
- Les logs n'allouent plus de copies de vecteurs d'embedding.
- Les intersections d'UIDs utilisent des `HashSet`.

## Definition of Done

- [ ] Build passes : `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` (0 erreur)
- [ ] Tests pass : `dotnet test HealthPlatform.Api.Mail.sln` (0 échec)
- [ ] Aucune requête de recherche sans borne (`Take`) dans `SemanticSearchRepository`
- [ ] Plus aucun `ToArray()` de vecteur d'embedding à des fins de logging
- [ ] Intersections d'UIDs en `HashSet` dans `SemanticSearchService`
- [ ] `PatientRepository` : liste des patients du jour bornée
- [ ] Unit tests : >= 1 test par méthode de recherche modifiée, incluant un test prouvant que le plafond est respecté (dataset > plafond → résultat borné)
- [ ] Integration test : endpoint de recherche via le pipeline DI complet (happy path + recherche sans résultat)
- [ ] Aucune donnée de santé en clair dans les logs (les termes de recherche, potentiellement nominatifs, ne sont pas loggés en clair)

## Manual Test Plan

- Lancer l'API : `cd Api/Mail && docker-compose up -d && dotnet run --project src/Api`
- Sur un compte de test avec >= 500 mails (données anonymisées), lancer une
  recherche full-text avec un terme très fréquent (ex. « compte rendu ») :
  les résultats s'affichent en moins de quelques secondes, identiques en tête de
  liste à la version précédente.
- Lancer une recherche sémantique : résultats cohérents, latence stable.
- Observer le working set du process pendant 10 recherches successives :
  pas de croissance mémoire marquée.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (LPS MSSanté)
- **Vague Ségur** : hors Ségur — optimisation technique
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable — la recherche n'altère pas le traitement de l'identité
- **Authentification PS** : inchangée
- **Habilitations** : non applicable
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé ; vigilance : ne pas introduire de log des termes de recherche en clair
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement HDS existant inchangé
- **AIPD / impact RGPD** : inchangé
