# todo-task-338.md — La recherche dit la vérité : une panne n'est plus « aucun résultat », chaque filtre demandé est appliqué, et les vues par étiquette sont couvertes

**Repos**: api-mail
**Dependencies**: — (aucune ; **à coordonner avec task-192**, qui touche les mêmes fichiers — voir « Coordination »)
**Epic**: E009
**Single frontend**: true
**Priorité**: **2** — le médecin qui cherche un compte rendu pendant une panne conclut qu'il **n'existe pas** ; un filtre désactivé renvoie toute la boîte ; la recherche par mot-clé ne fonctionne pas depuis une vue « Urgent ».

> **Origine.** Audit de détection de bugs du 2026-09-27
> (`Docs/audits/api-mail-audit-bugs-20260927.md`, **AUD-38**, **AUD-39**, **AUD-40**, **AUD-52**).

## Ce qui est établi (develop @ `14d58398`)

1. **Panne masquée (AUD-38)** — `SemanticSearchService.cs:110-121, 263-268, 283-297, 486-489, 544-547` :
   `catch (Exception ex) { … return Enumerable.Empty<…>(); }` — Postgres, pgvector ou fournisseur
   d'embeddings en panne → 200 `TotalResults = 0` ; en hybride, la partie sémantique disparaît sans
   signal ; `OperationCanceledException` avalée (règle 12 : erreurs au `GlobalExceptionHandler`, 499 central).
2. **Filtres ignorés (AUD-39)** — `SemanticSearchService.cs:62-75, 137, 689-733`,
   `SemanticSearchRepository.cs:663-781` : `PatientFilters` (LastName, Ins, PatientId),
   `StatusFilters.IsAnswered`/`IsDraft`, `DateFilters.MedicalDocumentDate*`/`BiologyResultDate*`, et les
   booléens de contenu à `false` sont **comptés actifs mais non appliqués** ; le chemin « filtres seuls »
   relance alors la requête avec `Take(int.MaxValue)`. Déclencheur réel : désactiver la pastille « PJ »
   dans Blazor envoie `HasAttachments = false` (`SearchMailComponent.razor:406`).
3. **Vues par étiquette (AUD-40)** — `SemanticSearchRepository.cs:395, 430, 467-471, 489-493, 512-517` :
   les requêtes plein texte comparent `m.FolderPath == "tag:Urgent"` sans `ParseTagFolder`
   (contrairement aux requêtes vectorielles et à `SearchByFiltersAsync`) → 0 résultat.
4. **Seuil double (AUD-52)** — `SemanticSearchService.cs:314, 331, 621-641`, `SearchController.cs:99` :
   `MinSimilarity` appliqué au dépôt puis sur le score hybride pénalisé (×0,8 / ×0,6) → au-delà de 0,6,
   plus aucun résultat trouvé seulement par mot-clé.

## Objective

Que la recherche **signale** une panne au lieu de rendre une liste vide, applique **chaque** critère
qu'elle accepte (ou le refuse explicitement), couvre les vues par étiquette en plein texte comme en
sémantique, et filtre sa pertinence **une seule fois**.

### Périmètre

1. **Pannes** : exceptions remontées (503 via `UnavailableException`, 499 pour l'annulation) ; mode
   hybride dégradé (une seule jambe disponible) **signalé explicitement** dans la réponse.
2. **Filtres** : tout critère accepté par le contrat est appliqué, ou rejeté en 400 ; `false` signifie
   « sans … » ; le chemin « filtres seuls » est borné comme les autres.
3. **Étiquettes** : le prédicat dossier/étiquette est partagé par les requêtes plein texte, vectorielles et filtres.
4. **Seuil** : un seul filtrage de pertinence, documenté.

### Coordination avec task-192

task-192 (dédup sur l'UID, casse, jokers, signal de troncature) modifie les mêmes méthodes et **le
contrat** (`SearchResponseDto`, dtos-mss). Ordre recommandé : task-192 d'abord, puis cette US ; si
cette US passe avant, le signal de mode dégradé est ajouté de façon compatible avec le futur contrat de task-192.

### Hors périmètre

- Dédup UID, casse, jokers, troncature (task-192).
- L'historique de recherche (jugé sain par l'audit).

## Definition of Done

- [ ] Build passes (0 errors) — `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` ; Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] **Tests rouges d'abord** (log des runs rouges dans le task file), rouges sur le code actuel :
  - [ ] dépôt de recherche qui lève → sur le code actuel liste vide 200 ; après correctif 503 `ProblemDetails`
  - [ ] recherche « filtres seuls » avec `HasAttachments = false` → sur le code actuel tout le dossier ; après correctif seulement les mails **sans** pièce jointe, dans la borne
  - [ ] recherche plein texte « Dupont » dans la vue `tag:Urgent` → sur le code actuel 0 ; après correctif les mails étiquetés qui correspondent
  - [ ] `MinSimilarity = 0,7`, résultat trouvé seulement par mot-clé avec score normalisé 1 → rendu
- [ ] Test : fournisseur d'embeddings en panne en mode hybride → résultats plein texte rendus **et** mode dégradé signalé
- [ ] Test : annulation client → 499 (pas de liste vide)
- [ ] Test : chaque filtre du contrat appliqué (un test par famille : patient, statut, dates documentaires, dates de biologie, contenu)
- [ ] Test d'intégration endpoint (règle 1b) : `POST` de recherche avec filtre patient → seuls les mails de ce patient
- [ ] Aucune requête de recherche brute ni INS dans les logs (cohérence task-184)

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost` ; Blazor connecté à une boîte de test seedée.
2. **Panne** : arrêter le conteneur Postgres de l'AppHost (ou couper l'accès à la base) et lancer une recherche → **Attendu** : message d'indisponibilité. Avant : « aucun résultat ».
3. **Pastille PJ** : sans texte, activer puis désactiver la pastille « PJ » → seuls les mails sans pièce jointe s'affichent. Avant : toute la boîte.
4. **Vue Urgent** : ouvrir la vue « Urgent », rechercher un nom de patient de test présent dans un mail urgent → il est trouvé. Avant : aucun résultat en mode mot-clé.
5. **Seuil** : régler la similarité minimale à 0,7, rechercher un nom propre → les mails qui le contiennent sont trouvés.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2
- **Exigences DSR honorées** : non applicable — fiabilité de la recherche dans la messagerie
- **INS** : le filtre patient par INS est appliqué côté serveur, sans INS dans les logs ni l'URL
- **Authentification PS** : inchangée
- **Habilitations** : inchangées — recherche limitée à la base du praticien
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé ; les pannes de recherche sont journalisées sans le texte recherché
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement inchangé
- **AIPD / impact RGPD** : inchangé

## Branches
- `api-mail` (pushed) : fix/task-338-search-tells-the-truth — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-338-search-tells-the-truth (depuis `origin/develop` @ `856a7089`, task-192 mergée — la coordination demandée est satisfaite)
- `dtos-mss` (pushed, créée par `/develop` — contrat modifié) : fix/task-338-search-tells-the-truth — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/fix/task-338-search-tells-the-truth
- Note règle 1b (réécrite le 2026-10-01, après la rédaction de cette task) : la DOD ne demande qu'un test d'intégration (filtre patient) ; `/develop` applique la règle de `CLAUDE.md` — un test d'intégration d'endpoint, vu rouge, par comportement modifié (503, 499, mode dégradé, filtres, vue étiquette, seuil).

## Develop log

- Repos touched : `api-mail`, `dtos-mss` (branche paresseuse, contrat modifié)
- DTOs published : `HealthPlatform.Dtos.Mss` 492.0.0 → **496.0.0** (run 36927315270) — ajout pur : `SearchResponseDto.IsDegraded` et `SearchResponseDto.DegradedSources` (codes stables `semantic`, `fulltext`)
- Interop published : no interop change
- Commits :
  - dtos-mss : `2aa32a7` feat(dto): la reponse de recherche signale un mode degrade — IsDegraded et DegradedSources
  - api-mail : `b649d19d` fix(search): la recherche dit la vérité — pannes signalées, chaque filtre appliqué, vues par étiquette, seuil unique (bump DTO 496.0.0 + `packages.lock.json`, seule la version DTO change)
  - api-mail : `3bf666b5` refactor(search): simplify pass (/simplify)
- Ce qui a changé :
  1. **AUD-38 — pannes** : plus aucun `catch` qui rend une liste vide (deux catch-all de premier niveau, le repli silencieux de l'embedding, deux repli plein texte). Toute panne non typée → `UnavailableException` (503, code `search_unavailable`, message sans donnée de santé ni texte recherché) ; annulation → 499 ; refus 409 (dimension, task-325) et 400 inchangés. Hybride : un moteur en panne n'empêche pas l'autre de répondre, la réponse porte `IsDegraded` / `DegradedSources` ; les deux en panne → 503. Les deux flux (boîte et patient) partagent un seul `RunEnginesAsync`.
  2. **AUD-39 — filtres** : appliqués par le repository — patient (nom en `ILike` échappé, INS exact, identifiant) lus sur **un même document**, répondu, brouillon, plage de dates de document, plage de dates de résultat de biologie, `false` = « sans » (pièce jointe, document, biologie) ; type de document inconnu → `ValidationException` (400) au lieu d'être ignoré ; chemin « filtres seuls » borné à `maxResults` (lecture de `maxResults + 1`), troncature signalée.
  3. **AUD-40 — étiquettes** : un seul prédicat `InFolder(IQueryable<Mail>, folderPath)` alimente les 14 jointures (vectorielles, embeddings, plein texte, par identifiants, filtres) ; les 5 requêtes plein texte / par identifiants comparaient `FolderPath == "tag:…"` littéralement.
  4. **AUD-52 — seuil** : `MinSimilarity` n'est plus appliqué qu'une fois, dans la requête de similarité ; le contrôleur ne refiltre plus sur le score hybride pénalisé (`SearchResultHelper.ToHits`).

### Tests d'intégration d'endpoint (règle 1b) — comportement → test → preuve rouge

Vraie route `POST /api/v1/search/semantic` ou `/search/patient`, vrai contrôleur, vrai service, vrai repository, base PostgreSQL dédiée par test (`PostgreSqlFixture.CreateIsolatedContextAsync`). Seuls simulés : le générateur d'embeddings (fournisseur externe) et l'historique Redis. **Preuve rouge : 21 cas sur 23 rouges sur le code d'avant le correctif, chacun pour la raison attendue** (extraits ci-dessous) ; les 2 autres sont des garde-fous du faux positif.

| Comportement lu dans la réponse réelle | Test (`SearchEndpointTruthIntegrationTests`) | Rouge sur le code d'avant |
|---|---|---|
| Base injoignable → 503 ProblemDetails (boîte) | `Semantic_DatabaseUnreachable_Returns503ProblemDetails` | `Expected: ServiceUnavailable Actual: OK` |
| Base injoignable → 503 ProblemDetails (patient) | `Patient_DatabaseUnreachable_Returns503ProblemDetails` | `Expected: ServiceUnavailable Actual: OK` |
| Fournisseur d'embeddings en panne, hybride → résultats plein texte + `IsDegraded`, `DegradedSources = [semantic]` | `Hybrid_EmbeddingProviderDown_ReturnsKeywordHitsAndFlagsDegradedMode` | `Assert.True() Expected: True Actual: False` |
| Fournisseur en panne, sémantique seul → 503 | `SemanticOnly_EmbeddingProviderDown_Returns503ProblemDetails` | `Expected: ServiceUnavailable Actual: OK` |
| Annulation → 499 | `Search_CancelledWhileQueryingTheProvider_Returns499` | `Expected: 499 Actual: 200` |
| Recherche complète → non dégradée | `Hybrid_EveryEngineAnswers_IsNotDegraded` | garde-fou (vert attendu) |
| Filtre patient par nom, INS, identifiant | `FiltersOnly_PatientFilter_KeepsOnlyThatPatientsMails` ×3 | `Assert.Single() … contained 2 items` ×3 |
| Requête + filtre patient → seuls ses mails (ligne de DOD) | `Query_WithPatientFilter_ReturnsOnlyThatPatientsMails` | `contained 2 items` |
| Répondu / brouillon | `FiltersOnly_StatusFilters_AppliesAnsweredAndDraft` ×2 | `contained 2 items` ×2 |
| Plage de dates de document | `FiltersOnly_MedicalDocumentDateRange_KeepsOnlyDocumentsInRange` | `contained 2 items` |
| Plage de dates de biologie | `FiltersOnly_BiologyResultDateRange_KeepsOnlyResultsInRange` | `contained 2 items` |
| `HasAttachments` / `HasMedicalDocuments` / `HasBiologyResults` = false → « sans » | `FiltersOnly_ContentFlagFalse_KeepsOnlyMailsWithout` ×3 | `contained 2 items` ×3 |
| Type de document inconnu → 400 ProblemDetails | `FiltersOnly_UnknownMedicalDocumentType_Returns400ProblemDetails` | `Expected: BadRequest Actual: OK` |
| Filtres seuls bornés à `maxResults`, tronqués signalés | `FiltersOnly_MoreMatchesThanMaxResults_IsBoundedAndFlaggedTruncated` | `Expected: 2 Actual: 3` |
| Recherche plein texte dans `tag:URGENT` et `TAG/URGENT` | `FullText_InTagView_FindsTheTaggedMailsThatMatch` ×2 | `The collection was empty` ×2 |
| `MinSimilarity = 0,7`, hybride, trouvé seulement par mot-clé → rendu | `Hybrid_HighMinSimilarity_StillReturnsKeywordOnlyHits` | `The collection was empty` |

Tests existants qui **figeaient le défaut**, réécrits sur le comportement attendu : `SearchByFiltersAsync_WithUnknownDocumentType_DoesNotFilterByLoinc` → `…_IsRefused` ; dans `SemanticSearchServiceTests` / `…CoverageTests`, six tests « …WhenRepositoryThrows_ReturnsEmpty… » / « …FallsBackToFullTextOnly » sans signal → `UnavailableException` ou mode dégradé signalé ; +3 unitaires (annulation non enveloppée, deux moteurs en panne → 503, plein texte seul en panne → `fulltext`). Le test de journalisation garde son assertion « longueur de la requête, jamais son texte ».

- Local build / test : ✓ api-mail — build 0 erreur ; suite complète **6 021 réussis, 0 échec**, 16 ignorés. Un rouge isolé au premier passage (`SeededThreadsAreCountableTests.TheCountedThreadsMatchTheSeededChains`, `DbUpdateException`) : vert en isolation (4/4) et au rejeu complet ; flaky pré-existant, troisième task qui le croise (188, 273, 338) — consigné en mémoire avec une piste (base isolée par test).
- Passe qualité (/simplify, 4 agents) :
  - Applied & committed : api-mail — 7 fichiers (`3bf666b5`) : un seul `RunEnginesAsync` pour les deux flux, restes du « vecteur nul » retirés, `BuildFilterOnlyResults` sans paramètre mort, chemin « filtres seuls » à `maxResults + 1` lignes au lieu de ×10, `EXISTS` / `NOT EXISTS` plutôt que `EXISTS(…) = @bool`, base isolée déplacée dans `PostgreSqlFixture` (plus de copie dans `TestSimilarityEndpointIntegrationTests`), `OkAsync` partagé, usings morts retirés
  - Skipped : (1) laisser le gestionnaire global choisir 503 / 500 — contredirait la DOD (dépôt qui lève → 503) ; (2) déplacer la validation du type de document dans le service — équivalent en effet ; (3) **garde contre la dérive « filtre compté actif » / « filtre appliqué »** (cause profonde d'AUD-39 : deux listes tenues à la main, `HasActive*Filters` côté service et `Apply*Filters` côté repository) — à porter par une task de suite (repository qui rend ce qu'il a appliqué, ou test par réflexion sur chaque propriété de `SearchFilterDto`)
  - Skipped (contract) : dtos-mss
- DOD self-check (10/10 vérifiables par commande) :
  - [x] Build 0 erreur ; tests 0 échec hors flaky pré-existant documenté
  - [x] Rouges d'abord, sur le code actuel (tableau ci-dessus) : dépôt qui lève → 503 ; « filtres seuls » `HasAttachments = false` → seuls les mails sans PJ, dans la borne ; « Dupont » dans `tag:Urgent` → trouvé ; `MinSimilarity = 0,7` mot-clé seul → rendu
  - [x] Fournisseur d'embeddings en panne en hybride → plein texte rendu **et** mode dégradé signalé
  - [x] Annulation → 499
  - [x] Chaque famille de filtres : patient, statut, dates documentaires, dates de biologie, contenu
  - [x] Test d'intégration endpoint avec filtre patient → seuls ses mails
  - [x] Aucune requête brute ni INS dans les logs : aucun nouveau log ne porte la requête ni un critère (le seul ajout journalise le **nom** du moteur en panne) ; le test de journalisation existant garde son assertion
- Next step : /sonar task-338

## Sonar log

- Mode A (chaîné), projet `healthplatform-api-mail`, serveur 25.6.0.109173 sur `localhost:9001` (conteneurs redémarrés), propriété `sonar.token`
- Itérations : 2 analyses (baseline + vérification)

### KPIs qualité

| Métrique | Baseline (itér. 1) | Final (itér. 2) |
|---|---|---|
| Issues new-code dans les fichiers de task-338 | 3 (S1067 ×3) | **0** |
| Issues new-code, tout le projet | 66 | 63 |
| `new_code_smells` | 64 | 61 |
| `new_bugs` / `new_vulnerabilities` | 2 / 0 | 2 / 0 |
| `new_coverage` (projet) | 98,2 % | 98,2 % |
| `new_coverage` des fichiers source de task-338 | 97,0–100 % | 96,0–100 % |
| `coverage` (projet) | 98,1 % | 98,0 % |
| `code_smells` (projet) | 68 | 65 |
| Ratings fiabilité / sécurité / maintenabilité | D / A / A | D / A / A |
| Hotspots new-code `TO_REVIEW` dans les fichiers de la task | 0 | 0 |
| **Quality Gate** | **ERROR** | **ERROR** |

- **Phase 1 (new code de task-338) : verte.** 3 × `csharpsquid:S1067` (trop d'opérateurs conditionnels) sur les filtres patient, dates de document et dates de biologie de `SemanticSearchRepository.cs`, corrigés (`7fa67268`) : un ensemble de documents restreint par critère présent, puis un seul `EXISTS`. Même sémantique « tous les critères sur le même document », et plus de `@x IS NULL OR` dans le SQL. Deux tests d'intégration ajoutés pour le prouver (`FiltersOnly_PatientCriteriaOnTwoDifferentDocuments_DoNotMatch`, `FiltersOnly_DocumentDatesOnEitherSideOfTheRange_DoNotMatch`), vus rouges par mutation (critères éclatés sur des `EXISTS` séparés).
- **Quality Gate ERROR non imputable à task-338** : `new_violations` 63 et `new_security_hotspots_reviewed` 0 % portent exclusivement sur des fichiers hors diff, entrés dans la new-code period avec des tasks déjà mergées (même constat que task-192).
- **Phase 2 (legacy)** : skipped — best-effort, non bloquante, hors périmètre.
- Conventions : `conventions/csharp.md` — nouvelle entrée **S1067** (filtre EF à critères optionnels : composer, pas une expression unique ; garder un test à deux enregistrements).
- Build / tests après correctif : 0 erreur ; domain 190, infrastructure 677, api 1 151, application 3 287 verts ; intégration verte hors trois tests « du jour » documentés, rouges entre 00:00 et 02:00 heure de Paris (exécution à 00:15, jour local ≠ jour UTC — rouges aussi sur `develop` dans cette fenêtre) et un flaky pré-existant au premier passage (`SeededThreadsAreCountableTests`, consigné).
- Next step : /lint-angular task-338

## Lint log

- `/lint-angular` : **skipped** — `client-angular` non listé dans `**Repos**:` (US backend-only).

## Lint mobile log

- `/lint-mobile` : **skipped** — `client-mobile` non listé dans `**Repos**:` (US backend-only).

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail + dtos-mss touchés | ✅ verte (1 flaky) | 24 verts, 1 flaky, 0 rouge, 0 quarantaine | voir la section Timings |
| angular | api-mail + dtos-mss touchés | ✅ verte | 25 verts, 0 flaky, 0 rouge, 0 quarantaine | voir la section Timings |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ branche de la task (`fix/task-338-search-tells-the-truth`, à jour de `develop` après merge de task-349)
- Checkout Angular joué : `feature/nova-rewriting-mss` @ `36021874` (branche humaine, mode code-only)
- Quarantaines : aucune
- Divergences ouvertes : aucune
- Parcours touchés sans spec e2e modifié : aucun (aucun écran touché)
- Démontage : complet (ports libres, aucun conteneur e2e résiduel)
- **Historique de l'étape** (trois passages) :
  1. voie Angular en **code 2** (`@playwright/test` non installé) → `npm ci`, prévention Step 0 bis ;
  2. voie Angular **rouge + parité** sur `E2E-COMPOSE-002`, test de task-349 présent sur la branche Angular → arrêt, `questions/task-338.md` ;
  3. après merge de task-349 sur `develop` : branche api-mail de task-338 synchronisée (`git merge origin/develop`, DTO 500.0.0 republié avec les deux contrats), clone mobile `develop` rattrapé en avance rapide (une révision de retard, `c6dadb4`) — prévention ajoutée au Step 0 bis → **vert**.
- Flaky : `E2E-DETAIL-002` (mobile), 2ᵉ occurrence au registre de `conventions/e2e.md`

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**Flaky (vert au second essai, non bloquant)** (1) :

- [mobile] « détail — bascule texte brut / HTML » (E2E-DETAIL-002)

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-CONTACT-001 | 1 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 1 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ⚠️ flaky |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 1 | headless | Créer puis supprimer un contact | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/268 — label `awaiting-human-merge`
- `dtos-mss` : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/37 — label `awaiting-human-merge` (HealthPlatform.Dtos.Mss 500.0.0 publié depuis la branche, porte aussi le contrat de task-349)
- `client-blazor`, `client-angular`, `client-mobile` : non listés — n'affichent pas encore `IsDegraded` ; task front à ouvrir (avec celle de task-192)

## Code Review Summary

- Validation `/review` : `dtos-mss` build 0 erreur ; `api-mail` build 0 erreur, **6 083 tests réussis, 0 échec**, 16 ignorés ; branches à jour de `origin/develop` (task-349 fusionnée en amont)
- DOD : 10/10 vérifiés par commande, Manual Test Plan différé au HAG
- **Verrou 4a (règle 1b)** : chaque comportement atteignable par l'endpoint → son test d'intégration d'endpoint → sa preuve rouge, détaillés dans le tableau du `## Develop log` (21 rouges sur le code d'avant, 2 par mutation pour la sémantique « même document », 2 garde-fous) ✅
- **Verrou 4b (E2E)** : `## E2E log` vert (mobile 24 + 1 flaky, Angular 25, parité verte) ✅
- **Verdict : APPROVED** — 0 bloquant, 4 suggestions :
  1. dérive structurelle « filtre compté actif » (service) / « filtre appliqué » (repository), cause profonde d'AUD-39 → task de suite (repository qui rend ce qu'il a appliqué, ou test par réflexion sur `SearchFilterDto`)
  2. `folderPath` vide = « tous les dossiers » partout désormais (cohérent, à connaître)
  3. fronts : afficher `IsDegraded` et le message d'indisponibilité (503)
  4. `SeededThreadsAreCountableTests` (flaky pré-existant, 3ᵉ task) : base isolée par test via `PostgreSqlFixture.CreateIsolatedContextAsync`

## Timings

*(généré par `tools/timing/report.sh --task task-338 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 1 min 01 s | — | — | — | — |
| /develop | ok | 6 min 02 s | 7 (2 min 08 s) | 8 (16 min 49 s) | — | dtos-mss 2B/0T, api-mail 5B/8T, merge develop (task-349) + DTO 500.0.0 |
| /sonar | ok | 24 min 55 s | 4 (1 min 04 s) | 12 (12 min 21 s) | 4 (4 min 44 s) | 2 itération(s), api-mail 4B/12T |
| /lint-angular | skipped | 2.0 s | — | — | — | client-angular non listé dans Repos |
| /lint-mobile | skipped | 2.1 s | — | — | — | client-mobile non listé dans Repos |
| /e2e | ok | 16 min 21 s | — | — | — | e2e ×9 (25 min 34 s), vert après merge task-349 et rattrapage du clone mobile ; 1 flaky E2E-DETAIL-002 |
| /review | ok | 5 min 58 s | 2 (25 s) | 1 (3 min 37 s) | — | dtos-mss 1B/0T, api-mail 1B/1T |
| **Total cycle** | | **54 min 24 s** | **13 (3 min 38 s)** | **21 (32 min 48 s)** | **4 (4 min 44 s)** | |

Autres commandes mesurées : nuget-wait ×2 (30 s), restore ×3 (2 min 24 s)
