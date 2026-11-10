# todo-task-439.md — Recherche plein texte fiable : accents, champs, tous les mots, tout l'historique

**Repos**: api-mail, dtos-mss
**Dependencies**: done-task-438
**Epic**: E022
**Single frontend**: true
**Priorité**: EPIC E022, demandée par l'humain le 2026-11-09. Absorbe task-436 (coût du plein texte), sur décision de
l'humain du même jour : « une seule refonte, une seule migration éventuelle ».

> **Origine.**
> - Campagne du 2026-11-09 : `Docs/audits/recherche-campagne-bugs-weda2-mobile-20261109.md`, défauts **R1 à R5**.
> - Coût : `Docs/audits/api-mail-volumetrie-plans-boite-11k-20261109.md` (ex-task-436), plans et `replay.py` dans
>   `Docs/audits/findings/plans/20261109-volumetrie-boite-11k/`.
> - Requêtes de référence et corpus : task-438. Les cas marqués « task-439 » y passent au vert ici.

## Ce qui est établi

**Ce que rate le médecin** (boîte de 11 178 mails, appels réels, 2026-11-09) :

| Défaut | Requête | Vérité terrain | Rendu |
|---|---|---|---|
| R1 accent oublié | `hemoglobine` | 804 messages contiennent « hémoglobine » | 2 (seuil 0,7) |
| R2 objet non cherché | `urgent` | 72 messages, dont 67 par l'objet seul | 5 |
| R3 historique ancien | `Catherine BERNARD` | 51 messages portent les deux noms | 22 ; **tous les manquants sont les plus anciens** |
| R4 un des mots (OU) | `Catherine BERNARD` | — | 28 résultats sur 50 n'ont qu'un des deux noms |
| R4 termes abandonnés | `bilan lipidique cholestérol total` | 35 messages ont les quatre mots | 27 ; « total » jamais cherché |
| R5 ponctuation | `cholestérol,` | 47 messages contiennent « cholestérol » | 0 |

**Causes** (`405da376`) :
- `SearchQueryHelper.FilterSearchTerms` : découpe sur les espaces seulement (la ponctuation reste collée), ignore les
  mots de 2 lettres ou moins, garde les **3 termes les plus longs** (`SemanticSearchRepository`, ligne 734).
- `MailContentsSinglePassSql` / `MedicalDocumentsSinglePassSql` (lignes 711 et 715) : `lower(Body) LIKE '%terme%'`,
  **sans repli des accents**, sur le **corps seul** des messages et des documents. Les termes sont combinés en **OU**.
- `SearchLimits.FullTextCandidatesPerTerm = 200` : chaque terme ne garde que ses 200 correspondances **les plus
  récentes** avant tout classement. Un nom fréquent épuise ce quota avec d'autres patients. Le test
  `Semantic_MoreMatchesThanTheWindow_KeepsTheMostRecentMails` fige ce comportement (marqué task-439 par task-438).

**Coût** (repris de task-436) : la recherche plein texte des contenus passe de 11,65 ms (156 mails) à **134,73 ms**
(11 178 mails), celle des documents de 8,69 à 31,70 ms. Cause : l'application renvoie à Postgres, en `ANY($2)`, les
identifiants de **tous** les contenus du dossier, puis met chaque corps en minuscules. L'index `pg_trgm` avait été
écarté par task-427 sur une boîte de 156 mails : verdict à remesurer à 11 000 mails.

**Déploiement** : une base est migrée à son premier accès, sous un sémaphore commun à toutes les boîtes du processus
(`BaseRepository.HandleEnvironmentDbSetupAsync`). Un index construit dans une migration ordinaire bloquerait l'ouverture
de toutes les boîtes (même contrainte que task-437).

## Objective

Le médecin trouve **tous** les messages de sa boîte qui contiennent ce qu'il a tapé, quelle que soit sa façon de le
taper, dans les champs où il s'attend à le trouver, sur tout l'historique de la boîte. Ceux qui contiennent tous ses mots
viennent d'abord.

Règles métier (décisions de l'humain du 2026-11-09) :
- **Accents, casse et ponctuation sans effet** : `hemoglobine`, `HÉMOGLOBINE`, `hémoglobine,` trouvent les mêmes
  messages. La requête est découpée en mots sur tout ce qui n'est ni lettre ni chiffre.
- **Champs cherchés** : objet, corps du message, corps des documents médicaux (CDA, HPRIM), nom et adresse de
  l'expéditeur, nom des pièces jointes.
- **Tous les mots d'abord** :
  - premier groupe : les messages qui contiennent **tous** les mots significatifs ;
  - second groupe, **séparé et signalé** : ceux qui n'en contiennent qu'une partie, du plus grand nombre de mots au plus
    petit ;
  - dans chaque groupe, du plus récent au plus ancien ;
  - chaque résultat dit à quel groupe il appartient (contrat, ci-dessous).
- **Tous les mots significatifs comptent**, jusqu'à 10 ; au-delà, la réponse le signale. Les mots vides restent ignorés.
- **Tout l'historique** : aucune correspondance n'est écartée parce qu'elle est ancienne. Le plafond de candidats par
  terme choisis parmi les plus récents disparaît.
- **Voir les suivants** : quand il y a plus de résultats que la page demandée, la réponse le dit (`isTruncated`) et le
  client peut demander la page suivante.
- **Règle 14 inchangée** : même base de la boîte, même verdict de l'opérateur, même trace de la recherche au nom de la
  personne réelle.

Contrat (`dtos-mss`, rétrocompatible) :
- chaque `hit` porte son **groupe de correspondance** (tous les mots / une partie des mots) ;
- la requête accepte une **position de départ** (page suivante) ;
- les champs existants (`uids`, `hits`, `isTruncated`, `isDegraded`) gardent leur sens. Les clients actuels, qui ne
  lisent que `uids`, continuent de fonctionner ; l'affichage des groupes et des pages suivantes est task-441.

Exigences de coût (reprises de task-436), mesurées sur la boîte de 11 178 mails :
- la partie plein texte d'une recherche ne renvoie plus à Postgres la liste des identifiants du dossier ;
- elle coûte **45 ms au plus** sur les contenus et **15 ms au plus** sur les documents, plans à l'appui, alors qu'elle
  cherche désormais dans plus de champs ;
- au moins deux pistes sont mesurées et consignées avant le choix (index sur un texte normalisé, `pg_trgm`, recherche
  plein texte Postgres, colonne de texte cherchable…) : taille, temps de construction, temps de requête ;
- **un index ne bloque pas les autres boîtes** : sa construction ne retarde l'ouverture d'aucune autre boîte, et une
  boîte dont l'index n'existe pas encore cherche quand même (mécanisme partagé avec task-437 si les deux en posent un).

### Hors périmètre

- Les résultats sémantiques et leur place dans la réponse : task-440. L'index vectoriel : task-437.
- L'affichage côté clients (groupes, pages suivantes, ordre) : task-441.
- La recherche avancée par filtres (inchangée), et `/search/patient` (inchangée, hors corpus des défauts constatés).

## Definition of Done

- [ ] Build passes (0 errors) : `HealthPlatform.Api.Mail.sln`, `HealthPlatform.Dtos.Mss.csproj`
- [ ] Tests pass (0 failures) : `HealthPlatform.Api.Mail.sln`
- [ ] **Les requêtes de référence de task-438 marquées « task-439 » sont vertes**, marquage retiré : accent oublié,
      majuscules, ponctuation, mot de l'objet, de l'expéditeur, du nom d'une pièce jointe, patient au long historique
      (rappel 100 % sur ses messages), plusieurs mots (tous les mots en tête, partiels signalés), plus de 3 mots
- [ ] **Test d'intégration de bout en bout (règle 1b), `POST /api/v1/Search/semantic`** en mode hybride, lu dans la
      réponse réelle :
      - un patient dont plus de 200 messages portent le nom : **tous** sont trouvés, les plus anciens compris, page par
        page ;
      - le groupe de correspondance de chaque `hit` est lu et vaut ce qu'il doit valoir ;
      - **vu rouge** sur le code d'avant (cas de task-438) et par mutation (plafond par terme réinjecté, puis restauré et
        recompilé), preuve consignée dans le `## Develop log`
- [ ] **Cas d'échec** : une requête sans mot significatif rend la même réponse qu'aujourd'hui (liste vide, sans
      erreur) ; une requête de plus de 10 mots le signale dans la réponse
- [ ] Le test `Semantic_MoreMatchesThanTheWindow_KeepsTheMostRecentMails` est **réécrit** selon la nouvelle règle (tout
      l'historique, page par page), pas supprimé
- [ ] Contrat `dtos-mss` publié (NuGet) et consommateurs .NET mis à jour ; rétrocompatibilité vérifiée : un client qui
      ne lit que `uids` reçoit la même forme de réponse
- [ ] **Coût** mesuré sur la boîte de 11 178 mails par `replay.py` (formes nouvelles) : plein texte des contenus
      ≤ 45 ms, des documents ≤ 15 ms ; tableau des pistes mesurées dans le `## Develop log`
- [ ] Si un index est posé : migration auditée (règle 7c), construction sans blocage des autres boîtes prouvée par un
      test d'intégration (une boîte A s'ouvre pendant la construction de l'index d'une boîte B), base neuve et base
      existante testées
- [ ] **A/B au banc** (tir court 1400 → 1996, IA simulée, contre `bilan-apres` dans la même session) : temps SQL des
      formes de recherche, p50 / p95 de l'étape « recherche »
- [ ] Outil de campagne de task-438 rejoué sur la boîte de formation de Virginie : R1 à R5 disparus, tableau consigné
- [ ] Aucune donnée de santé en clair dans les logs (termes de recherche compris)
- [ ] **Prévention (règle d'or)** : consigne dans `conventions/csharp.md` : un plafond de candidats ne se choisit jamais
      par ancienneté avant le classement ; une liste d'identifiants qui croît avec la boîte ne se renvoie jamais en
      paramètre

## Manual Test Plan

1. Lancer le backend sur la boîte de formation de Virginie : `cd Api/Mail/src/AppHost && dotnet run`.
2. Dans weda2 (connexion par la CPS de Virginie), boîte de réception, rechercher successivement :
   `hemoglobine`, `HÉMOGLOBINE`, `cholestérol,`, `urgent`, `Catherine BERNARD`, `bilan lipidique cholestérol total`.
3. Attendu :
   - `hemoglobine` et `HÉMOGLOBINE` rendent les mêmes messages, qui contiennent « hémoglobine » ;
   - `cholestérol,` trouve les messages qui contiennent « cholestérol » ;
   - `urgent` trouve les messages dont l'objet contient « URGENT » ;
   - `Catherine BERNARD` : les messages de Catherine BERNARD d'abord, y compris les plus anciens (l'outil de campagne
     compte 51 messages ; l'affichage des groupes arrive avec task-441) ;
   - dans Seq, la route `POST /api/v1/Search/semantic` reste rapide.
4. Rejouer l'outil de campagne de task-438 : R1 à R5 n'apparaissent plus.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie MSSanté du praticien)
- **Vague Ségur** : hors Ségur — fiabilité de la recherche dans la messagerie
- **Exigences DSR honorées** : non applicable — aucune exigence DSR ne porte sur la recherche de la messagerie
- **INS** : non applicable — la recherche ne lit ni n'écrit l'INS ; un nom de patient est cherché comme un mot
- **Authentification PS** : inchangée — PSC (e-CPS), niveau eIDAS substantiel
- **Habilitations** : inchangées — verdict de l'opérateur MSSanté sur la boîte (règle 14)
- **Interop CI-SIS** : non applicable — les documents CDA et HPRIM déjà analysés sont cherchés, pas échangés
- **Tracé PGSSI-S** : inchangé — chaque recherche tracée au nom de la personne réelle (`MailSearch`), 3 653 jours ;
  les termes ne sont jamais écrits dans les journaux
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — un éventuel index ou texte normalisé porte des données de santé et vit dans la base de la
  boîte, avec ses sauvegardes et sa suppression
- **AIPD / impact RGPD** : inchangé — aucune donnée nouvelle ; les structures de recherche sont dérivées de la boîte

## Branches
- `api-mail` (pushed) : feat/task-439-recherche-plein-texte-fiable-accents — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-439-recherche-plein-texte-fiable-accents
- `dtos-mss` (paresseuse) : branche `feat/task-439-recherche-plein-texte-fiable-accents` créée par `/develop` depuis `origin/develop` au moment où il touche le contrat (groupe de correspondance, position de départ)

## Timings

*(généré par `tools/timing/report.sh --task task-439 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 18 s | — | — | — | — |
| /develop | ok | 1 h 40 min | 4 (39 s) | 6 (16 min 54 s) | — | api-mail 4B/6T |
| /sonar | ok | 21 min 50 s | 2 (57 s) | 10 (16 min 00 s) | 4 (1 min 35 s) | 2 itération(s), api-mail 2B/10T |
| /lint-angular | skipped | 0.4 s | — | — | — | client-angular non touché |
| /lint-mobile | skipped | 0.4 s | — | — | — | client-mobile non touché |
| **Total cycle** | | **2 h 02 min** | **6 (1 min 37 s)** | **16 (32 min 54 s)** | **4 (1 min 35 s)** | |

Autres commandes mesurées : nuget-wait ×1 (15 s)

## Develop log

- **Repos touchés** : dtos-mss, api-mail. client-blazor non bumpé : hors `**Repos**`, resté à `HealthPlatform.Dtos.Mss 533.0.0` (il ne lit pas la recherche ; à aligner par la task qui le touchera).
- **DTOs publiés** : `HealthPlatform.Dtos.Mss 578.0.0` (`SearchMatchGroup`, `SearchHitDto.MatchGroup`, `SearchRequestDto.Offset` et `MaxSearchTerms`, `SearchResponseDto.IsQueryTruncated`), rétrocompatible : `uids`, `hits`, `isTruncated`, `isDegraded` gardent leur sens.
- **Commits** : dtos-mss `feat(dto)` ; api-mail `5c5ba62e` (bump), `93695949` (feature), `07e67bde` (passe qualité).
- **Ce qui change pour le médecin** :
  - les mots sont lus comme il les tape : accents, casse et ponctuation sans effet, jusqu'à 10 mots (`SearchTerms`, jumeau C# de `search_normalize` = `lower(unaccent(…))`) ;
  - les champs cherchés sont l'objet, le corps, les documents médicaux, le nom et l'adresse de l'expéditeur, et le nom des pièces jointes ;
  - l'ordre : tous les mots d'abord, puis une partie des mots, puis les proches par le sens. Chaque `hit` porte son groupe ;
  - tout l'historique, page par page (`offset`). Le plafond des 200 plus récents par terme a disparu.
- **Texte cherchable** :
  - colonnes `"SearchText"` générées, stockées, sur `Mails`, `MailContents`, `MailAttachments` et `MailMedicalDocuments`, avec un index trigrammes ;
  - construites en tâche de fond au premier usage de la recherche, hors du sémaphore de migration, deux à la fois par processus, sous verrou consultatif. La recherche normalise à la volée en attendant ;
  - la migration `20261110120000` est instantanée (extensions `unaccent` et `pg_trgm`, fonction `search_normalize`).
- **Pistes mesurées** (copie `srch_lab` de la boîte de formation, 11 178 mails, médiane de 5 passages, `Docs/audits/findings/plans/20261110-recherche-task-439/`) :

  | Piste | Taille des index | Construction | 1 mot (tous champs) | 4 mots (tous champs) |
  |---|---|---|---|---|
  | A — normalisation `translate` à la volée, sans index | — | — | 1 346 ms | 5 379 ms |
  | B — index trigrammes sur expression `translate` | 18 Mo | 3,9 s | 190 ms | 720 ms |
  | B' — index trigrammes sur expression `unaccent` | 18 Mo | 2,8 s | 41 ms | 150 ms |
  | **C — colonne générée normalisée + index trigrammes (retenue)** | 18 Mo | 3,0 s (colonnes) + 2,4 s (index) | **11 ms** | **29 ms** |

  Le coût de la piste B vient de la revérification de chaque ligne candidate, qui refait la normalisation. Avec la piste C, cette revérification est un simple `LIKE` sur un texte déjà normalisé.
- **Coût des nouvelles formes** (`replay_task439.py`, forme composée par EF, `results-indexed.json`) :
  - plein texte des contenus : **≤ 32 ms** (objectif 45) ;
  - plein texte des documents : **≤ 10 ms** (objectif 15) ;
  - les deux : ≤ 40 ms.

  Sans index, pendant la construction, la même requête rend les mêmes lignes en 60 à 400 ms (`results-fallback.json`).
- **Vérité terrain** : sur la copie, `hemoglobine` trouve 805 messages (vérité de la campagne : 804 ; rendus avant : 2) et `urgent` en trouve 72 (rendus avant : 5).
- **Règle 1b — tests d'intégration de bout en bout** (`POST /api/v1/Search/semantic`, vraie pile, PostgreSQL) :
  - `SearchExactFirstHybridIntegrationTests` : mode hybride avec moteur sémantique joué. 230 messages anciens d'un patient sous 460 homonymes partiels récents sont tous trouvés page par page, chacun dans le bon groupe. Le mot est trouvé dans chaque champ, sans accent, en majuscules, avec une virgule. Plus de 10 mots sont signalés. Une requête sans mot significatif rend une liste vide sans erreur ;
  - `FullTextSearchSinglePassIntegrationTests` : tout l'historique page par page. Ce test réécrit `Semantic_MoreMatchesThanTheWindow_KeepsTheMostRecentMails`, qui figeait R3. Les jokers sont des séparateurs ;
  - `SearchTextIndexIntegrationTests` : une base neuve se construit. Une base existante répond la même chose avant et après la construction, puis lit la colonne indexée. La construction bloquée de la boîte B ne retarde pas la boîte A ;
  - `SearchTextNormalizationMigrationTests` : le coureur FluentMigrator de production pose la fonction, la base et le code normalisent à l'identique, et le texte cherchable se construit (règle 7c).
- **Vu rouge** :
  - sur le code d'avant : les 10 cas « task-439 » du corpus de task-438 (constat du `## Develop log` de task-438). Ils sont verts ici, marques retirées ;
  - par mutation, chaque mutation restaurée et recompilée (`--no-incremental`) :

    | Mutation | Tests au rouge |
    |---|---|
    | Plafond de 200 réinjecté | 2 (tout l'historique, page par page) |
    | Objet, expéditeur et pièces jointes non cherchés | 6 (champs, corpus `objet`, `expediteur`, `piece-jointe`…) |
    | Groupe de correspondance faussé | 3 |
    | Page suivante ignorée | 2 |
- **Tests migrés** (agent, 8 fichiers) vers `FindFullTextMatchesAsync`. Ceux qui affirmaient l'ancienne fusion pondérée ou l'ancienne fenêtre sont réécrits selon la nouvelle règle ; deux sont supprimés (une fusion qui n'existe plus, un test qui appelait son propre stub).
- **Piège retrouvé, 5ᵉ récidive de 53300 (« too many clients »)** :
  - les bases jetables de `SemanticSearchRepositoryCoverageIntegrationTests` gardaient un pool Npgsql par test ;
  - mesuré au pic : 98 connexions, dont 95 inactives ;
  - elles passent maintenant par `fixture.CreateIsolatedContextAsync` (sans pool) ;
  - 7 autres fichiers de tests de migration gardent le même motif : à corriger dans une task dédiée.
- **Passe qualité (/simplify)** :
  - Appliqué : six formes SQL précalculées ; route de provisionnement unique (`BaseRepository`) ; clé de verrou namespacée (`MigrationHelper`) ; `RankExactFirst` allégé ; lecture bornée à la page quand aucun filtre n'est actif ; `Forget` retiré ; un seul seuil de longueur ;
  - Écarté après mesure : la normalisation une fois par ligne (247 ms contre 88 ms pour un mot) ;
  - Écarté, hors périmètre ou suite à donner :
    - un verrou de migration par base au lieu du sémaphore global, qui permettrait de poser les colonnes dans une migration ordinaire, au prix d'environ 5 s au premier accès de la boîte ;
    - normaliser aussi les motifs en SQL ;
    - construire les bases de fixture par FluentMigrator ;
    - aligner la recherche par patient (`/search/patient`, `FilterSearchTerms`), qui garde l'ancien moteur.
- **Build et tests locaux** : `HealthPlatform.Api.Mail.sln` sans erreur ni avertissement sur les fichiers touchés. Tests : domain 210, infrastructure 727, api 1 378, application 4 053, intégration 1 187 (+ 17 écartés, dont « mot absent » mobile marqué task-440), 0 échec.
- **DoD — restent à faire, ce que la forge ne peut pas faire seule** :
  - **A/B au banc** (tir court 1400 → 1996, IA simulée, contre `bilan-apres`) : non joué. Il mobilise le banc de charge plus d'une heure, à décider avec l'humain ;
  - **rejouer l'outil de campagne sur la boîte de Virginie** : il faut une session réelle (`proxy_session_id`) et l'AppHost lancé sur cette branche (Manual Test Plan, point 4).
- Next step : /sonar task-439

## Sonar log

**Mode A** (chaîné depuis `/develop`), `api-mail`, branche `feat/task-439-…`, 2 analyses (build `Release`).

| KPI | Baseline (analyse de task-438) | Itération 1 | Final |
|---|---|---|---|
| Quality Gate | OK | OK | **OK** |
| Bugs / Vulnérabilités | 0 / 0 | 0 / 0 | 0 / 0 |
| Code smells | 0 | 0 | **0** |
| Hotspots à revoir | 0 | 0 | 0 |
| Couverture globale | 97,9 % | 97,7 % | **97,8 %** |
| Duplication | 0,4 % | 0,4 % | 0,4 % |
| Ratings (fiabilité / sécurité / maintenabilité) | A / A / A | A / A / A | A / A / A |

Tests de l'analyse finale : 7 559, 0 échec.

**Phase 1 — nouveau code** : 0 issue. Quatre trous de couverture sur le nouveau code, fermés (`727128fc`) :
- `SearchTextIndex` : la préparation découverte au catalogue (index construit par un autre processus) et la construction qui
  s'efface quand un autre pod tient le verrou → deux tests d'intégration. Fichier couvert à 100 %.
- `BaseRepository.ProvisioningConnectionString` : route bornée et nommée avec un contexte utilisateur, `null` sans → deux tests
  unitaires.
- `SemanticSearchRepository` : `?? string.Empty` mort sur `FolderPath` (non nullable), retiré.

Les lignes non couvertes restantes de `SemanticSearchRepository` (24) et de `BaseRepository` (4 conditions) sont antérieures à la
task.

**Phase 2 — dette ancienne** : rien à traiter (0 issue ouverte). L'issue `xUnit1004` assumée par task-438 a disparu avec la
réécriture du test qui figeait R3.

**Conventions** : aucune règle Sonar corrigée à la main, aucune entrée.

## Lint log

- `/lint-angular` : skip — client-angular non touché par la task.
- `/lint-mobile` : skip — client-mobile non touché par la task.
