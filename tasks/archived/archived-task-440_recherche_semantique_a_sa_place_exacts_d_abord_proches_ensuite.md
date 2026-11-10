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
| /e2e | ok | 19 min 41 s | — | — | — | e2e ×3 (18 min 50 s) |
| /review | ok | 6 min 40 s | 2 (16 s) | 1 (5 min 29 s) | — | dtos-mss 1B/0T, api-mail 1B/1T |
| /tech-writer | ok | 45 s | — | — | — | — |
| **Total cycle** | | **1 h 12 min** | **10 (1 min 28 s)** | **8 (25 min 23 s)** | **2 (45 s)** | |

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

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail et dtos-mss touchés | ✅ verte | 60 verts, 0 flaky, 0 rouge, 0 quarantaine | 9 min 12 s |
| angular | api-mail et dtos-mss touchés | ✅ verte | 73 verts, 0 flaky, 0 rouge, 1 quarantaine (E2E-COMPOSE-002, verte) | 9 min 39 s |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ branche de la task (`feat/task-440-…`), inchangé par la task
- Quarantaines : [angular] E2E-COMPOSE-002, correction task-350 (posée par l'humain, verte à ce passage)
- Divergences ouvertes : aucune
- Parcours touchés sans spec e2e modifié : aucun écran touché (task backend ; l'affichage des sections est porté par E023, task-445 et task-450)
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

- `dtos-mss` : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/59 — label `awaiting-human-merge`
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/356 — label `awaiting-human-merge`

Ordre de merge : dtos-mss, puis api-mail (le paquet 581.0.0 est déjà publié ; api-mail le consomme).

## Code Review Summary

**APPROVED — 0 bloquant, 5 suggestions.** Build et tests verts (7 596 tests, 0 échec), DoD vérifiée, `## E2E log`
vert, Quality Gate OK.

- **Règle 1b** :
  - seuil unique du serveur, `minSimilarity` ignoré, seuil appliqué rendu → `ReferenceQuery_SameAnswerWhateverTheClientThreshold`, 24 rouges sur le code d'avant ;
  - mot sans rapport → réponse vide → `mot-absent`, rouge sur le code d'avant (mobile) et sous la mutation « seuil 0,10 » ;
  - exacts d'abord, sans doublon, section lue sur chaque `hit` → `Hybrid_VerySimilarNeighbours_…`, rouge sous la mutation « fusion mêlée » ;
  - rattrapage par le sens → `sens-*` et `SearchSimilarThresholdCalibrationTests`, rouges sur le code d'avant (weda2) et sous la mutation « seuil 0,10 » ;
  - moteur sémantique en panne → `Hybrid_EmbeddingProviderDown_…` (test existant, section `AllTerms` désormais lue).
- **Sécurité** : aucune entrée nouvelle, aucun journal nouveau ; le diagnostic journalise le seuil et la longueur de la
  requête, jamais son texte.
- **Suggestions** :
  1. le mode `SemanticOnly` applique aussi 0,45 : voulu, à confirmer au test manuel ;
  2. publier une métrique « proches rendus par recherche » (calibration faite sur des textes courts) ;
  3. rattraper les fautes de frappe par les trigrammes de task-439 ;
  4. aligner `/search/patient` ;
  5. retirer le `minSimilarity` encore enregistré par `SearchHistoryService` en même temps que le champ.
- **Test instable rencontré** : `EmailReadingUseCaseTests.ExpandThread…`, une fois rouge pendant la passe Sonar, vert
  isolé et dans les trois suites complètes ; consigné en mémoire de session.
- **Reste à l'humain** : rejouer l'outil de campagne sur la boîte de Virginie (Manual Test Plan).

## Merged

Mergé le 2026-11-10 par l'humain (`/merge task-440 --i-tested`), squash, CI `develop` verte sur les deux dépôts.

- `dtos-mss` #59 → `b40e096ca36526b90e6dc26330b7329836877a05`
- `api-mail` #356 → `83a7bb37a4153ff46954a379c38f8954460bac0b`

Branches `feat/task-440-recherche-semantique-a-sa-place-exacts-d` supprimées (distante et locale) sur les deux dépôts ;
label `awaiting-human-merge` retiré. Aucune branche staging (task lancée hors `/forge`).
