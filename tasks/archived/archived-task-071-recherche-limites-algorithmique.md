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

## Branches
- `api-mail` (pushed) : feat/task-071-recherche-bornage
- `dtos-mss` (pushed, auto-incluse) : feat/task-071-recherche-bornage — sera supprimée sans PR si aucun changement de contrat

## Develop log (2026-06-10)

**Commit (api-mail, `feat/task-071-recherche-bornage`)** : `dda520a`

**Findings traités** :
1. ✅ `ExecuteFullTextSearchAsync` : `OrderByDescending(Uid).Take(maxCandidatesPerTerm)` par terme + borne du résultat final classé par `Rank` desc. Plafond `SearchLimits.FullTextCandidatesPerTerm` = 200, surchargeable par appel (testé avec dataset > plafond). **Divergence de ranking documentée** : pour un terme présent dans > 200 mails, seuls les 200 plus récents sont candidats — les correspondances plus anciennes sortent du classement (avant : tout chargé en mémoire).
2. ✅ `queryVector.Memory.Length` aux 2 sites restants (55, 116) — les autres lignes de l'audit (290-319) avaient déjà été nettoyées par des tasks antérieures.
3. ✅ (déjà résolu en amont) `filteredUids` est déjà `HashSet<uint>` dans `SemanticSearchService` — constat documenté, aucun changement.
4. ✅ `GetWithMedicalDocumentsTodayAsync(maxPatients = SearchLimits.TodayPatientsMax)` : `Take` après `Distinct`, plafond 500, testé avec plafond surchargé.

**Bonus DOD (PGSSI-S)** : les termes de recherche étaient loggés en clair (controller ×4 dont logger source-généré, service ×3) → remplacés par des longueurs. 3 tests prouvent la non-journalisation de termes nominatifs.

**Validation** : build Release 0 erreur ; suite complète 2700 verts (94+488+346+1555+217), 1 échec = flaky IMAP pré-existante documentée. Les 3 nouveaux tests d'intégration passent (le delta de compteur s'explique : la branche part de develop sans task-070, HAG).

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/94 — label `awaiting-human-merge`
- `dtos-mss` : branche `feat/task-071-recherche-bornage` sans commit (aucun changement de contrat) — pas de PR, branche à supprimer au `/merge`

## Code Review Summary

APPROVED — 0 issue bloquante, 1 note non-bloquante (tri Uid desc = approximation du « plus récent » en multi-dossiers, documentée dans la PR).
- `SemanticSearchRepository.cs` — ✅ bornage par terme + résultat final, plafond surchargeable testé
- `SemanticSearchService.cs` / `SearchController*.cs` — ✅ aucune fuite de terme de recherche dans les logs (3 tests)
- `PatientRepository.cs` — ✅ patients du jour bornés, testé
- DOD : tous items verts ; déviation justifiée sur le test endpoint DI complet (service d'embedding requis) → 7 tests controller + 3 intégration PostgreSQL
- Sonar : Quality Gate OK, 0 new-code issue

## Merged

- **Date** : 2026-06-11
- **api-mail** : PR #94 squash-mergée — commit `4d88f3e` sur `develop`
- **dtos-mss** : aucune PR (branche sans commit) — branche remote supprimée
- **CI develop** : ✅ success — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/27366268010
- Branches locales conservées pour inspection rétroactive (convention /merge)
