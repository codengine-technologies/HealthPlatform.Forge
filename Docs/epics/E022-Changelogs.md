# E022 — Recherche fiable — Changelogs

> **Audience** : équipes techniques (backlog, dette, revue de PR).
> **Vue produit** : [E022-recherche-fiable.md](E022-recherche-fiable.md)
> **Dernière mise à jour** : 2026-11-10

---

## Historique détaillé des changelogs

### v0.3 — task-440 : la recherche par le sens à sa place — exacts d'abord, proches ensuite (2026-11-10)

- **PRs** : dtos-mss [#59](https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/59), api-mail
  [#356](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/356), label `awaiting-human-merge`.
  Ordre de merge : dtos-mss, puis api-mail.
- **NuGet** : `HealthPlatform.Dtos.Mss` **581.0.0**, documentation seulement, rétrocompatible :
  - `SearchRequestDto.MinSimilarity` est déprécié et ignoré ;
  - `SearchResponseDto.MinSimilarity` dit le seuil appliqué ;
  - `SearchMatchGroup.Similar` désigne la section des proches.
- **Seuil unique** : `SearchLimits.SimilarMinSimilarity = 0,45`, appliqué par `SemanticSearchService` aux deux recherches
  vectorielles de la boîte.
  - `SemanticSearchOptions.MinSimilarity` est supprimé : aucun client ne pilote plus le seuil (avant : 0,7 dans weda2,
    0,1 sur le mobile) ;
  - `/search/patient` garde son seuil (hors périmètre).
- **Calibration** (`SearchSimilarThresholdCalibrationTests`, embeddings réels `text-embedding-3-small`, 6 requêtes
  « par le sens » ajoutées au corpus, jugement clinique dans `SearchReferenceQueries`) :
  - à 0,45 : 5 proches sur 5 pertinents, aucun bruit sur un mot sans rapport ;
  - à 0,425 : 75 % de pertinence ; à 0,10 : 4 % ;
  - rattrapé : « hypercholestérolémie » (4 bilans lipidiques), « anémie » (hémoglobine basse) ;
  - perdu, faute de similarité : potassium, BPCO, « psoriasys », arythmie, ferritine ;
  - chaque requête « par le sens » déclare ce qui est rattrapé (`Caught`) ; le test casse si le modèle d'embeddings
    change.
- **Règle 1b** :
  - tests : `ReferenceQuery_SameAnswerWhateverTheClientThreshold` (24 requêtes),
    `Hybrid_VerySimilarNeighbours_NeverPassAheadOfTheExactMatches_AndNoMailIsRepeated`, verdict de référence enrichi
    (exacts d'abord, doublons, rattrapage) ;
  - vus rouges : les 24 requêtes de « même réponse », `mot-absent` (mobile) et le rattrapage (weda2) sur le code
    d'avant ; puis les mutations « fusion mêlée » et « seuil 0,10 ».
- **Tests** : domain 210, infrastructure 729, api 1 375, application 4 054, intégration 1 228 (+ 16 écartés), 0 échec ;
  e2e mobile 60, Angular 73, parité verte.
- **Sonar** : Quality Gate OK, 0 issue, couverture 97,8 %, nouveau code 96,0 %.
- **Test instable rencontré** : `EmailReadingUseCaseTests.ExpandThread…` (socket, une fois en Release), consigné.
- **Prévention** : `conventions/csharp.md`, `seuil-fixe-par-le-serveur`.
- **Suites proposées** :
  - rattraper les fautes de frappe par les trigrammes de task-439 ;
  - aligner `/search/patient` ;
  - publier une métrique « proches rendus par recherche » ;
  - retirer le réglage de similarité des clients (task-445, task-450).
- **Reste à l'humain** : rejouer l'outil de campagne sur la boîte de Virginie.

### v0.2 — task-439 : recherche plein texte fiable — accents, champs, tous les mots, tout l'historique (2026-11-10)

- **PRs** : dtos-mss [#58](https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/58), api-mail
  [#355](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/355), label `awaiting-human-merge`.
  Ordre de merge : dtos-mss, puis api-mail.
- **NuGet** : `HealthPlatform.Dtos.Mss` **578.0.0** (`SearchMatchGroup`, `SearchHitDto.MatchGroup`,
  `SearchRequestDto.Offset` et `MaxSearchTerms = 10`, `SearchResponseDto.IsQueryTruncated`), rétrocompatible.
  client-blazor reste à 533.0.0.
- **Absorbe task-436** (coût du plein texte).
- **Moteur** :
  - `SearchTerms` normalise en C# comme `public.search_normalize(text)` en SQL (`lower(unaccent(…))`, IMMUTABLE). Les mots
    de 3 lettres et plus sont gardés, sans mots vides, 10 mots au plus ;
  - une requête unique `FindFullTextMatchesAsync` cherche dans l'objet, le nom et l'adresse de l'expéditeur, le corps, le
    nom des pièces jointes et les documents médicaux. Classement : tous les mots, puis une partie, du plus récent au plus
    ancien, puis les résultats sémantiques ;
  - plafond de 200 candidats par terme retiré, pagination par `offset`, borne de sécurité `FullTextMatchesMax = 25 000` ;
  - colonnes générées et stockées `"SearchText"`, avec index GIN `gin_trgm_ops`. `SearchTextIndex` les construit en tâche
    de fond au premier usage de la recherche, hors du sémaphore de migration : 2 constructions par processus, verrou
    consultatif, `lock_timeout` 2 s, index invalide reconstruit. En attendant, la recherche normalise à la volée ;
  - migration `20261110120000` instantanée (extensions `unaccent` et `pg_trgm`, fonction) ;
  - `/search/patient` garde l'ancien moteur.
- **Coût** (copie de la boîte de 11 178 messages) :
  - plein texte des contenus ≤ 32 ms (objectif 45), des documents ≤ 10 ms (objectif 15) ;
  - pendant la construction, 60 à 400 ms à la volée ;
  - piste C (colonne générée + trigrammes) retenue : 11 ms pour un mot, contre 1 346 ms pour A, 190 ms pour B et 41 ms
    pour B'.
- **A/B au banc** (1400 → 1996 médecins, IA simulée, tirs A, B et A' dans la même session) :
  - B contre A' : recherche −10 % au p50 et au p95, SQL du plein texte −34 % par recherche, une requête au lieu de deux ;
  - le ralentissement A → A' vient de l'état des bases, pas du code ;
  - `"SearchText"` pèse ≈ 7 % du volume d'une base ;
  - +0,3 ms de SQL par requête HTTP restent non tranchés (attente d'entrées-sorties juste après la préconstruction) ;
  - rapports : `Docs/audits/findings/plans/20261110-recherche-task-439/ab-banc/`.
- **Règle 1b** :
  - tests : `SearchExactFirstHybridIntegrationTests`, `FullTextSearchSinglePassIntegrationTests` (réécrit
    `Semantic_MoreMatchesThanTheWindow_KeepsTheMostRecentMails`), `SearchTextIndexIntegrationTests`,
    `SearchTextNormalizationMigrationTests` ;
  - vus rouges : les 10 cas « task-439 » du corpus de task-438, plus 4 mutations (plafond 2, champs 6, groupe 3,
    page 2).
- **Tests** : domain 210, infrastructure 727, api 1 378, application 4 053, intégration 1 187 (+ 17 écartés), 0 échec ;
  e2e mobile 60, Angular 73, parité verte.
- **Sonar** : Quality Gate OK, 0 bug, 0 vulnérabilité, 0 code smell, couverture 97,9 → 97,8 %, quatre trous du nouveau
  code fermés.
- **53300 (5ᵉ récidive)** : les bases jetables de `SemanticSearchRepositoryCoverageIntegrationTests` passent sans pool.
  7 fichiers de tests de migration gardent le motif.
- **Préventions** (`conventions/csharp.md`) :
  - `recherche-plafond-par-anciennete` ;
  - une migration qui change une colonne lue par la recherche supprime d'abord `"SearchText"`.
- **Reste à l'humain** : rejouer l'outil de campagne sur la boîte de Virginie (R1 à R5).

### v0.1 — task-438 : le filet d'abord, un corpus et des requêtes de référence (2026-11-10)

- **PRs** : api-mail [#354](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/354), client-mobile
  [#122](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/122), label `awaiting-human-merge` ;
  client-angular code-only, `front/e2e/mss-e2e/specs/functional.e2e.ts` non commité sur `feature/nova-mss-weda-integration`.
- **NuGet** : aucun (pas de changement de contrat).
- **Origine** : campagne du 2026-11-09 sur la boîte de formation de Virginie (11 178 mails), défauts R1 à R9,
  `Docs/audits/recherche-campagne-bugs-weda2-mobile-20261109.md`.
- **Filet** (`Api/Mail/tests/mss.mail.integration.tests/Search/Reference/`) :
  - corpus fictif de 560 messages, dont 30 porteurs d'embeddings réels (`text-embedding-3-small`, 48 vecteurs
    pré-calculés dans `search-reference-embeddings.json`, aucun appel externe en test) ;
  - 18 requêtes × 2 profils (weda2 `minSimilarity` 0,7, mobile 0,1), en mode hybride, 50 résultats, sur
    `POST /api/v1/Search/semantic` à travers la vraie pile ;
  - verdict selon quatre règles (rappel, tous les mots d'abord, mot absent, dossier courant) et tableau
    `search-reference-report.md`.
- **Défauts prouvés rouges** (`SEARCH_REFERENCE_KNOWN_DEFECTS=1`) : 11 sur 36, marqués avec la task qui les corrige.
  - task-439 : accent, majuscules, objet, ponctuation (weda2) ; expéditeur, pièce jointe, patient au long historique
    (deux profils) ;
  - task-440 : mot absent (mobile).
- **Mutation des verts** : `SemanticSearchRepository.InFolder` sans filtre de dossier → 14 cas verts tombent.
- **e2e** : `E2E-SEARCH-002` v1 (mot rare accentué) et `E2E-SEARCH-003` v1 (numéro de dossier), requis sur mobile et
  Angular, seed `mail-non-lu-2` (`E2eSeedMessage.ExtraBodyText`). Mutation « le plein texte ne lit plus le corps »
  (`lower(d."Body")` → `lower(left(d."Body", 0))`) : 002 et 003 rouges sur les deux clients, 0 résultat au lieu de 1,
  alors qu'`E2E-SEARCH-001` restait vert.
- **Outillage** : `tests/search-quality/embed_corpus.py` (embeddings manquants), `tests/search-quality/campagne.py`
  (campagne sur une boîte de développement, API locale et session réelle seulement, jamais le test-bypass).
- **Tests** :
  - api-mail : domain 210, infrastructure 728, application 4 031, api 1 378, intégration 1 166 (+ 28 écartés), 0 échec ;
    `ImapServiceTests` instable connu, rejoué isolé ;
  - client-mobile : 1 417 tests ;
  - weda2 et mss-lib : 107 + 136 fichiers de test ;
  - e2e : mobile 60, Angular 73, parité verte.
- **Sonar** : Quality Gate OK.
  - Baseline : 0 bug, 0 vulnérabilité, 0 code smell, couverture 97,9 %.
  - Après correction : CA1859 ×3 corrigés, et 1 `xUnit1004` assumé sur `Semantic_MoreMatchesThanTheWindow_KeepsTheMostRecentMails`.
    Ce test fige R3 ; il reste marqué task-439, qui le réécrit.
- **Préventions** :
  - `conventions/csharp.md` : `recherche-jugee-comme-un-medecin`, CA1859 (17 occurrences), xUnit1004 ;
  - `conventions/e2e.md` : ligne « trou du filet » de la recherche ;
  - `agents/sonar.md` : un `Skip` qui cite une task n'est jamais retiré.

---

## Annexe A — Cartographie des briques applicatives

| Brique | Fichiers |
|---|---|
| Filet de référence | `Api/Mail/tests/mss.mail.integration.tests/Search/Reference/` (`SearchReferenceCorpus`, `SearchReferenceOracle`, `SearchReferenceQueries`, `SearchReferenceVerdict`, `SearchReferenceFixture`, `SearchReferenceQualityTests`, `PrecomputedEmbeddings`) |
| Moteur de recherche | `Api/Mail/src/Infrastructure/Repositories/MailDb/SemanticSearchRepository.cs`, `Api/Mail/src/Application/Services/Implementation/SemanticSearchService.cs`, `SearchQueryHelper`, `Api/Mail/src/Application/Helpers/SearchTerms.cs` |
| Seuil des proches | `Api/Mail/src/Application/Models/SearchLimits.cs` (`SimilarMinSimilarity`), `Api/Mail/tests/mss.mail.integration.tests/Search/Reference/SearchSimilarThresholdCalibrationTests.cs` |
| Texte cherchable | `Api/Mail/src/Infrastructure/Repositories/MailDb/SearchTextSchema.cs`, `SearchTextIndex.cs`, migration `20261110120000_AddSearchTextNormalization` |
| Contrat | `Dtos/SearchMatchGroup.cs`, `Dtos/SearchRequestDto.cs`, `Dtos/SearchResultDto.cs` |
| Seed et catalogue e2e | `Api/Mail/tests/mss.mail.testing.shared/E2eSeedPlan.cs`, `Api/Mail/e2e/scenarios.yml` |
| Parcours e2e | `Client/Mobile/e2e/specs/functional.spec.ts`, `Client/Angular/front/e2e/mss-e2e/specs/functional.e2e.ts` |
| Outillage | `Api/Mail/tests/search-quality/` |

---

## Annexe B — Inventaire fonctionnel daté (2026-11-10)

- Requêtes de référence : 24 (dont 6 « par le sens »), sur 2 profils, soit 48 cas, tous verts, aucun défaut connu ;
  24 contrôles « même réponse quel que soit le seuil du client » ; seuil des proches calibré (`SearchSimilarThresholdCalibrationTests`).
- Parcours e2e de recherche : 3 (`E2E-SEARCH-001` à `003`), sur 2 clients.

---

## Annexe C — Tasks ayant contribué à cet EPIC

| Task | Statut | Contribution | Règles |
|---|---|---|---|
| task-438 | archived (mergée) | Filet : corpus et requêtes de référence, E2E-SEARCH-002/003, outil de campagne | RG-E022-01 à 05 mesurées |
| task-439 | archived (mergée) | Plein texte : accents, champs, tous les mots, tout l'historique (absorbe task-436) | RG-E022-01, 02, 03 |
| task-440 | done (PRs ouvertes) | Sémantique : exacts d'abord, proches ensuite, seuil unique serveur | RG-E022-04 |
| task-441 | retirée | Reprise par l'EPIC E023 : task-445 (weda2), task-450 (mobile) | RG-E022-04 (affichage) |
