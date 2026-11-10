# todo-task-440.md — Recherche sémantique à sa place : exacts d'abord, proches ensuite

**Repos**: api-mail, dtos-mss
**Dependencies**: done-task-439 (même fusion des résultats, même champ de contrat ; task-438 est déjà requise par 439)
**Epic**: E022
**Single frontend**: true
**Priorité**: EPIC E022, demandée par l'humain le 2026-11-09. Décision de l'humain : « exacts d'abord, proches
ensuite » — les correspondances exactes en tête, puis une section de résultats proches sous un seuil unique calibré ;
un mot absent ne ramène aucun résultat exact.

> **Origine.** Campagne du 2026-11-09 : `Docs/audits/recherche-campagne-bugs-weda2-mobile-20261109.md`, défauts **R6**
> et **R7** (et la part sémantique de R1). À coordonner avec task-437 (index vectoriel), qui change la requête
> vectorielle mais pas la fusion.

## Ce qui est établi

| Requête | Seuil 0,7 (défaut weda2) | Seuil 0,1 (défaut mobile) |
|---|---|---|
| `zorglubine` (absent de la boîte) | 0 | **50 résultats sans rapport** |
| `psoriasis` (6 messages) | 6 | 6 bons, puis **44 qui ne contiennent pas le mot** |
| `hemoglobine` (sans accent) | 2 | 50, tous pertinents : la similarité **rattrape** l'accent |
| `urgent` (67 messages par l'objet seul) | 5 | 5 exacts, puis 45 voisins |

- **Fusion** (`SemanticSearchService.MergeAndScoreResults` / `BuildHybridResult`, `405da376`) : un résultat trouvé par
  les deux moteurs vaut `0,6 × similarité + 0,4 × score plein texte` ; par la similarité seule, `similarité × 0,8` ;
  par le plein texte seul, `score normalisé × 0,6`. Les deux sources sont **mêlées** dans un seul classement : un voisin
  sémantique vague peut passer devant un message qui contient le mot exact.
- **Seuil** : `maxDistance = 1 − minSimilarity`, fourni par chaque client. weda2 prend le réglage de la personne
  (`UserSettingsDto.MinSimilarity`, défaut **0,7** ; la boîte de Virginie porte 0,1 pour deux personnes et 0,7 pour
  deux autres) ; le mobile prend **0,1** (stockage local). Pour la même recherche, `psoriasis` rend 6 résultats dans
  weda2 et 50 sur le mobile.
- À 0,1, la recherche sémantique rend **toujours** ses voisins les plus proches, même lointains : aucun seuil ne
  protège d'un mot absent.
- Aucun test ne joue la recherche sémantique de bout en bout (constat de task-438).

## Objective

Les correspondances exactes passent toujours en tête. La recherche par le sens complète, sans jamais noyer : ses
résultats forment une section à part, et n'y entrent que s'ils sont réellement proches de la requête, selon un seuil
unique, calibré sur le corpus de référence, identique pour tous les clients et toutes les personnes.

Règles :
- **Deux sections dans la réponse**, dans cet ordre :
  1. **les correspondances exactes** (groupes « tous les mots » puis « une partie des mots », task-439) ;
  2. **les résultats proches** : trouvés par la similarité seule, absents de la première section, au-dessus du seuil.
  Un message trouvé par les deux moteurs est un résultat exact : il n'est pas répété dans les proches.
- **Un seuil unique, fixé par le serveur** et calibré sur le corpus de task-438 : les résultats proches rendus pour
  les requêtes de référence sont pertinents dans au moins **90 %** des cas (jugés par les attendus du corpus). Le seuil
  et sa calibration sont consignés.
- **Le réglage du client ne décide plus** : `minSimilarity` envoyé par un client est ignoré (contrat déprécié, accepté
  pour la compatibilité) ; le réglage de la personne n'influe plus sur la recherche. Son retrait de l'interface est
  task-441.
- **Mot absent** : aucun résultat exact ; des résultats proches seulement s'il en existe au-dessus du seuil. Pour un mot
  sans rapport avec la boîte (`zorglubine`), la réponse est vide.
- **Le rattrapage par le sens reste** : une formulation différente (synonyme, abréviation médicale courante, faute de
  frappe) peut trouver des messages en section « proches ». Task-440 complète le corpus de task-438 avec des requêtes
  de ce type, et leurs attendus.
- **Panne d'un moteur** : inchangé — l'autre répond, `isDegraded` le signale.
- **Règle 14 inchangée.**

Contrat (`dtos-mss`, rétrocompatible) : chaque `hit` dit s'il est **exact** (avec son groupe, task-439) ou **proche** ;
`minSimilarity` est déprécié dans la requête.

### Hors périmètre

- L'index vectoriel et le coût de la requête vectorielle : task-437.
- L'affichage des sections dans les clients et le retrait du réglage de similarité de l'interface : task-441.
- L'assistant IA, qui a ses propres usages de la similarité.

## Definition of Done

- [ ] Build passes (0 errors) : `HealthPlatform.Api.Mail.sln`, `HealthPlatform.Dtos.Mss.csproj`
- [ ] Tests pass (0 failures) : `HealthPlatform.Api.Mail.sln`
- [ ] **Les requêtes de référence de task-438 marquées « task-440 » sont vertes**, marquage retiré : mot absent (réponse
      vide), mot rare (aucun voisin intercalé avant les exacts), mêmes résultats quel que soit le `minSimilarity` envoyé
- [ ] **Test d'intégration de bout en bout (règle 1b), `POST /api/v1/Search/semantic`** en mode hybride, embeddings
      pré-calculés du corpus, lu dans la réponse réelle :
      - les exacts précèdent tous les proches ; aucun message n'apparaît dans les deux sections ;
      - la section de chaque `hit` est lue et vaut ce qu'elle doit valoir ;
      - deux requêtes identiques avec `minSimilarity` 0,1 et 0,9 rendent la même réponse ;
      - **vu rouge** sur le code d'avant (cas de task-438) et par mutation (fusion mêlée réinjectée), consigné
- [ ] **Cas d'échec** : moteur sémantique en panne → les exacts sont rendus, `isDegraded` vrai, `degradedSources`
      « semantic », lu dans la réponse réelle
- [ ] **Calibration du seuil** consignée dans le `## Develop log` : courbe pertinence / seuil sur le corpus, seuil retenu,
      ≥ 90 % de résultats proches pertinents ; requêtes « par le sens » ajoutées au corpus de task-438
- [ ] Contrat `dtos-mss` publié et consommateurs .NET mis à jour ; un client qui ne lit que `uids` reçoit les exacts puis
      les proches, dans cet ordre
- [ ] Outil de campagne rejoué sur la boîte de formation de Virginie : `zorglubine` vide, `psoriasis` sans voisins avant
      les 6 exacts, même réponse pour les deux seuils
- [ ] Aucune donnée de santé en clair dans les logs (termes de recherche et vecteurs compris)
- [ ] **Prévention (règle d'or)** : consigne dans `conventions/csharp.md` : un seuil qui décide de ce que voit le médecin
      est fixé par le serveur et calibré sur un corpus, jamais laissé à chaque client

## Manual Test Plan

1. Lancer le backend sur la boîte de formation de Virginie : `cd Api/Mail/src/AppHost && dotnet run`.
2. Dans weda2 puis sur le mobile, rechercher `zorglubine`, `psoriasis`, `infarctus`.
3. Attendu :
   - `zorglubine` : aucun résultat, dans les deux clients ;
   - `psoriasis` : les 6 messages qui contiennent le mot, et les mêmes dans les deux clients ;
   - `infarctus` : les messages qui contiennent le mot, puis éventuellement des messages proches (affichés à part à
     partir de task-441).
4. Changer le réglage de similarité dans les paramètres de weda2 : le résultat d'une recherche ne change pas.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie MSSanté du praticien)
- **Vague Ségur** : hors Ségur — fiabilité de la recherche
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : inchangée — PSC (e-CPS), niveau eIDAS substantiel
- **Habilitations** : inchangées — verdict de l'opérateur MSSanté (règle 14)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé — `MailSearch` au nom de la personne réelle, 3 653 jours ; ni terme ni vecteur journalisé
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — embeddings et résultats dans la base de la boîte, inchangés
- **AIPD / impact RGPD** : inchangé — l'usage de la similarité existe déjà ; seule sa présentation change

## Branches
- `api-mail` (pushed) : feat/task-440-recherche-semantique-a-sa-place-exacts-d — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-440-recherche-semantique-a-sa-place-exacts-d
- `dtos-mss` (paresseuse) : branche `feat/task-440-recherche-semantique-a-sa-place-exacts-d` créée par `/develop` depuis `origin/develop` au moment où il touche le contrat (section exact / proche, `minSimilarity` déprécié)

## Timings

*(généré par `tools/timing/report.sh --task task-440 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 21 s | — | — | — | — |
| /develop | ok | 33 min 19 s | 7 (52 s) | 2 (11 min 08 s) | — | api-mail 6B/2T, dtos-mss 1B/0T |
| /sonar | ok | 11 min 56 s | 1 (20 s) | 5 (8 min 44 s) | 2 (45 s) | 1 itération(s), api-mail 1B/5T |
| /lint-angular | skipped | 0.4 s | — | — | — | client-angular non touché |
| /lint-mobile | skipped | 0.4 s | — | — | — | client-mobile non touché |
| **Total cycle** | | **45 min 37 s** | **8 (1 min 12 s)** | **7 (19 min 53 s)** | **2 (45 s)** | |

Autres commandes mesurées : nuget-wait ×1 (25 s), restore ×1 (22 s)

## Develop log

- **Repos touchés** : dtos-mss (branche créée par `/develop`), api-mail.
- **DTOs publiés** : `HealthPlatform.Dtos.Mss 581.0.0`, documentation seulement, rétrocompatible :
  - `SearchRequestDto.MinSimilarity` est déprécié et ignoré par la recherche de la boîte ;
  - `SearchResponseDto.MinSimilarity` dit le seuil appliqué par le serveur ;
  - `SearchMatchGroup.Similar` est la section « proches », après tous les exacts.

  La section de chaque `hit` existe depuis task-439 (`matchGroup` : `AllTerms` / `SomeTerms` = exact, `Similar` = proche) : aucun champ nouveau n'était nécessaire.
- **Commits** :
  - dtos-mss : `feat(dto)` ;
  - api-mail : `68808224` (bump 581), `2c6088f1` (feature), `8a7ebb6f` (passe qualité).
- **Ce qui change pour le médecin** :
  - **un seuil unique, fixé par le serveur** (`SearchLimits.SimilarMinSimilarity = 0,45`) pour tous les clients et toutes les personnes. Le `minSimilarity` envoyé (0,7 dans weda2, 0,1 sur le mobile) n'entre plus dans la recherche : l'option n'existe plus dans `SemanticSearchOptions`. La recherche par patient (`/search/patient`) garde son seuil, hors périmètre ;
  - les exacts d'abord, puis les proches (ordre posé par task-439, désormais protégé par un test avec des voisins très proches) ;
  - un mot sans rapport avec la boîte (`zorglubine`) ne rend plus rien.
- **Calibration du seuil** (`SearchSimilarThresholdCalibrationTests`, embeddings réels `text-embedding-3-small` pré-calculés, corpus de task-438 + 6 requêtes « par le sens », jugement clinique écrit à la main dans `SearchReferenceQueries`) :

  | Seuil | Proches rendus | Pertinents | Pertinence | Pertinents « par le sens » perdus (sur 11) | Bruit sur un mot sans rapport |
  |---|---|---|---|---|---|
  | 0,10 (mobile) | 568 | 20 | 4 % | — | — |
  | 0,250 | 144 | 15 | 10 % | 2 | 1 |
  | 0,300 | 72 | 13 | 18 % | 3 | 0 |
  | 0,350 | 40 | 11 | 28 % | 3 | 0 |
  | 0,400 | 12 | 7 | 58 % | 4 | 0 |
  | 0,425 | 8 | 6 | 75 % | 5 | 0 |
  | **0,450 (retenu)** | **5** | **5** | **100 %** | **6** | **0** |
  | 0,500 | 4 | 4 | 100 % | 7 | 0 |
  | 0,550 | 0 | 0 | — | 11 | 0 |

  - **Pourquoi 0,45** : c'est le plus bas seuil qui tient l'engagement de pertinence (≥ 90 %). À 0,425, un voisin sans rapport entre : « echocardiographie » ramène l'échographie abdominale (0,448), et la pertinence tombe à 75 %.
  - **Ce que le seuil rattrape par le sens** : « hypercholestérolémie » retrouve les 4 bilans lipidiques (0,51 à 0,54) ; « anémie » retrouve l'hémoglobine basse (0,479).
  - **Ce qu'il perd**, faute de similarité suffisante avec ce modèle : « potassium » et la kaliémie (0,276), « BPCO » et la spirométrie (< 0,20), la faute de frappe « psoriasys » (0,383), « arythmie cardiaque » et le Holter (0,429), « anémie » et la ferritine (0,407). Chaque requête « par le sens » déclare ce qui est rattrapé (`Caught`). Le test casse si le seuil rattrape moins (régression) ou plus (le modèle a changé, recalibrer).
  - **Limite** : le corpus compte 30 messages vectorisés, aux textes courts. Les mails réels sont plus longs ; le rejeu sur la boîte de Virginie (Manual Test Plan) reste la validation terrain.
- **Règle 1b — tests d'intégration de bout en bout** (`POST /api/v1/Search/semantic`, vraie pile, PostgreSQL et pgvector) :
  - `SearchReferenceQualityTests.ReferenceQuery_FindsWhatTheMailboxHolds` (24 requêtes × 2 profils, embeddings réels). Le verdict lit la section de chaque `hit` et vérifie :
    - exacts d'abord, aucun message rendu deux fois ;
    - mot absent : réponse vide ;
    - rattrapage par le sens relevé ;
  - `SearchReferenceQualityTests.ReferenceQuery_SameAnswerWhateverTheClientThreshold` : la même réponse (ordre et groupes) avec `minSimilarity` 0,1 et 0,9, et `minSimilarity` de la réponse égal au seuil du serveur ;
  - `SearchExactFirstHybridIntegrationTests.Hybrid_VerySimilarNeighbours_NeverPassAheadOfTheExactMatches_AndNoMailIsRepeated` : des exacts non vectorisés face à deux voisins à similarité 1 ;
  - **cas d'échec** : `SearchEndpointTruthIntegrationTests.Hybrid_EmbeddingProviderDown_ReturnsKeywordHitsAndFlagsDegradedMode` (moteur sémantique en panne → l'exact est rendu, section `AllTerms`, `isDegraded`, `degradedSources = ["semantic"]`).
- **Vu rouge** :
  - sur le code d'avant (tests nouveaux, service inchangé) :
    - `mot-absent` sur le profil mobile ;
    - `sens-anemie` et `sens-pathologie` sur le profil weda2 (le seuil 0,7 écartait tout) ;
    - les 24 requêtes de `SameAnswerWhateverTheClientThreshold` ;
  - par mutation, restaurée puis recompilée (`--no-incremental`) :

    | Mutation | Tests au rouge |
    |---|---|
    | M1 — fusion mêlée réinjectée (proches et exacts triés ensemble, 0,8 × similarité + 0,6 × score des mots) | `Hybrid_VerySimilarNeighbours_…` : les deux voisins passent devant le message qui porte les deux mots |
    | M2 — seuil abaissé à 0,10 | `mot-absent` (weda2 et mobile) ; calibration : 20 proches pertinents sur 568 (4 %) |

  - Constat : M1 survit aux 72 requêtes de référence. Au seuil de 0,45, un proche plafonne à environ 0,44 en score pondéré, sous un exact (0,6). C'est le seuil qui protège ces requêtes. Le test dédié couvre le cas où il ne suffit pas (exact pas encore vectorisé).
- **Passe qualité (/simplify)** : 4 relectures (réutilisation, simplification, efficacité, altitude).
  - Appliqué :
    - distance maximale en constante, plus de paramètre de seuil sur les deux recherches vectorielles ;
    - plus de copie locale du seuil dans le contrôleur de diagnostic ;
    - `VectorSearchResult.SimilarityScore` réutilisé ;
    - vérification « embeddings manquants » partagée (`PrecomputedEmbeddings.AssertComplete`) ;
    - règle « mot sans rapport » partagée (`ReferenceQuery.IsUnrelated`) ;
    - bruit calculé une fois par candidat ;
    - verdict sans copie répétée.
  - Écarté :
    - retirer le mécanisme des défauts connus (`KnownDefects`) : documenté, il servira aux tasks d'E023 ;
    - ne jouer qu'un profil client : la matrice weda2 / mobile prouve la requête réelle de chaque client.
- **Build et tests locaux** : `HealthPlatform.Api.Mail.sln` sans erreur ni avertissement. Tests : domain 210, infrastructure 729, api 1 375, application 4 054, intégration 1 228 (+ 16 écartés), 0 échec.
- **Aucune donnée de santé dans les journaux** : aucun journal nouveau. Le diagnostic journalise le seuil du serveur et la longueur de la requête, jamais son texte.
- **Prévention (règle d'or)** : `conventions/csharp.md`, entrée `seuil-fixe-par-le-serveur`.
- **Suites proposées (hors task)** :
  - rattraper les fautes de frappe par les trigrammes déjà posés par task-439 (`similarity()` de `pg_trgm`), là où les embeddings échouent (« psoriasys » 0,383) ;
  - aligner le seuil de `/search/patient` ;
  - retirer le réglage de similarité des clients (part weda2 en task-445, mobile en task-450).
- **DoD — reste à faire par l'humain** : rejouer l'outil de campagne sur la boîte de Virginie (`zorglubine` vide, `psoriasis` sans voisins avant les 6 exacts, même réponse pour les deux seuils).
- Next step : /sonar task-440

## Sonar log

**Mode A** (chaîné depuis `/develop`), `api-mail`, branche `feat/task-440-…`, 1 analyse (build `Release`).

### KPIs qualité (baseline → final)

| KPI | Baseline (analyse de task-439) | Final |
|---|---|---|
| Quality Gate | OK | **OK** |
| Bugs / Vulnérabilités | 0 / 0 | 0 / 0 |
| Code smells | 0 | **0** |
| Hotspots à revoir | 0 | 0 |
| Couverture globale | 97,8 % | **97,8 %** |
| Couverture du nouveau code | — | **96,0 %** |
| Duplication | 0,4 % | 0,4 % |
| Ratings (fiabilité / sécurité / maintenabilité) | A / A / A | A / A / A |

**Phase 1 — nouveau code** : 0 issue. Rien à corriger, aucune itération supplémentaire.

**Phase 2 — dette ancienne** : 0 issue ouverte sur le projet.

**Tests de l'analyse** : domain 210, application 4 054, infrastructure 729, api 1 375, intégration 1 227 + 1 rouge.
Le rouge, `EmailReadingUseCaseTests.ExpandThreadShouldReturnAllRelatedEmailsAsyncAsync`, est une `SocketException` au
bout de 21 s, sur la lecture de fil, sans lien avec la recherche. Il est vert dans les deux suites complètes de
`/develop`, et vert deux fois isolé en Release. C'est un test instable, observé pour la première fois, consigné en
mémoire de session.

**Conventions** : aucune règle Sonar corrigée à la main, aucune entrée.

## Lint log

- `/lint-angular` : skip — client-angular non touché par la task.
- `/lint-mobile` : skip — client-mobile non touché par la task.
