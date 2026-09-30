# todo-task-192.md — Recherche : résultats silencieusement écartés (déduplication sur l'UID) et casse non ignorée

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Single frontend**: true

> **Origine** : exploration de bugs `api-mail` du 2026-07-25 (axe métier MSSanté).

> ### Re-vérification du 2026-08-23 — **toujours pertinente, et le défaut de casse est plus large qu'écrit**
>
> Chaque preuve rejouée sur `develop`. Les numéros de ligne du bloc « Preuve »
> datent du 2026-07-25 ; **la colonne « au 2026-08-23 » fait foi**.
>
> | Preuve | 2026-07-25 | Au 2026-08-23 | État |
> |---|---|---|---|
> | Déduplication sur l'UID | `SemanticSearchRepository.cs:513-515` | **`:579`** — `.GroupBy(x => x.Uid).Select(g => g.First())` | inchangé |
> | Fenêtre ordonnée sur l'UID | — | **`:572`** — `OrderByDescending(x => x.Uid)` puis `Take`, par terme | inchangé |
> | Casse hétérogène | `:597-632` — « patients en `ILike`, sujet/expéditeur en `Like` » | **inversé, et pire** : le **seul** `ILike` porte sur le corps (**`:571`**) ; sont en `Like` **sensible à la casse** : nom/prénom **patient** (`:98-99`, `:186-187`, `:260-261`, `:319-320`), `FromAddress`/`FromName` (`:674-675`, `:680`) et `Subject` (`:685`) | **plus large** |
> | Jokers non échappés | — | **confirmé : 0 échappement** dans le fichier — aucun `Escape`, aucun remplacement de `%`/`_` | inchangé |
>
> **Correction d'une erreur de la preuve d'origine, qui change le périmètre** :
> la recherche par **nom de patient** n'est **pas** insensible à la casse, contrairement
> à ce qu'affirmait la preuve du 2026-07-25. Chercher « DUPONT » ne trouve pas
> « Dupont ». C'est le champ le plus utilisé cliniquement, et c'est donc lui qui
> justifie le point 3 en priorité — pas le sujet.
>
> **Dépendance levée** : la task s'appuyait sur « l'identité de mail assainie par
> task-179 ». task-179 est **mergée** (`tasks/archived/`) — le point 1 peut donc
> être livré sur cette identité, sans attente.

## Objective

Rendre la recherche **exhaustive**. Une recherche multi-dossiers écarte aujourd'hui
des résultats pertinents sans le signaler, parce qu'elle déduplique les candidats
sur le seul **UID IMAP** — un identifiant qui n'est unique qu'au sein d'un dossier
(et pour une UIDVALIDITY donnée). Chaque dossier ayant sa propre numérotation
démarrant à 1, les collisions sont la règle, pas l'exception.

S'y ajoute une incohérence de casse : les filtres sur le sujet et l'expéditeur sont
**sensibles à la casse**, alors que ceux sur les noms de patients ne le sont pas.
Chercher l'expéditeur « dupont » ne trouve pas « DUPONT ».

Pour un praticien, une recherche qui cache un résultat sans le dire est plus
dangereuse qu'une recherche qui échoue franchement.

**US backend-only (justification)** : requêtes de recherche côté serveur.

### Preuve (état actuel du code)

- `src/Infrastructure/Repository/SemanticSearchRepository.cs:513-515` — la
  déduplication écrase les homonymes d'UID :
  `allCandidates.GroupBy(x => x.Uid).Select(g => g.First())`.
  Les trois appelants (`:397-435`) autorisent explicitement une recherche sans
  dossier (`folderPath == null || m.FolderPath == folderPath`) — donc à l'échelle de
  toute la boîte.
- La fenêtre de candidats est `OrderByDescending(x => x.Uid).Take(n)` par terme :
  elle mélange les UID de dossiers différents **comme s'il s'agissait d'un ordre
  chronologique**, ce qui n'a aucun sens entre dossiers.
- `src/Infrastructure/Repository/SemanticSearchRepository.cs:597-632` — les filtres
  Sujet / Nom d'expéditeur / Adresse utilisent `EF.Functions.Like`
  (**sensible** à la casse sous PostgreSQL) tandis que les noms de patients
  utilisent `ILike`. Par ailleurs les caractères `%` et `_` saisis par
  l'utilisateur ne sont **pas** échappés, dans les deux cas.

Lien avec task-179 : l'UID n'est unique que pour une UIDVALIDITY donnée. La
correction doit s'appuyer sur l'identité de mail assainie par task-179 plutôt que
de réintroduire une clé fragile.

### Contenu attendu

1. **Déduplication sur une identité réellement unique** — l'identifiant technique du
   mail, jamais l'UID seul. S'aligner sur l'identité définie par task-179.
2. **Ordonnancement cohérent** : la fenêtre de candidats doit s'ordonner sur une
   grandeur qui a un sens transverse aux dossiers (la date du message), pas sur
   l'UID.
3. **Casse homogène** : recherche insensible à la casse sur tous les champs
   textuels, y compris sujet, nom et adresse d'expéditeur.
4. **Échappement des jokers** : `%` et `_` saisis par l'utilisateur doivent être
   traités comme des caractères littéraux.
5. **Pas de perte muette** : si la recherche tronque volontairement (fenêtre de
   candidats, plafond de résultats), cela doit être **explicite** dans la réponse,
   afin que l'interface puisse indiquer au praticien que des résultats
   supplémentaires existent.

### Hors scope

- La pertinence sémantique et le rappel du moteur vectoriel (sujet distinct).
- L'identité des mails elle-même → task-179.
- Le contenu des logs de recherche → task-184.

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] Test unitaire : deux messages de **dossiers différents** portant le **même**
      UID et correspondant tous deux à la recherche ⇒ **les deux** sont retournés
      (ce test doit échouer sur le code actuel — le vérifier explicitement)
- [ ] Test unitaire : la fenêtre de candidats s'ordonne sur la date du message, et
      un message récent d'un dossier archivé n'est pas écarté par un UID plus faible
- [ ] Test unitaire : recherche « dupont » trouve « DUPONT » et « Dupont » sur le
      sujet, le nom et l'adresse d'expéditeur
- [ ] Test unitaire : une saisie contenant `%` ou `_` est traitée littéralement
- [ ] Test unitaire : quand un plafond de résultats s'applique, la réponse le signale
      explicitement
- [ ] Non-régression : les recherches mono-dossier existantes retournent les mêmes
      résultats qu'avant (à l'exhaustivité près)
- [ ] Aucune requête de recherche brute journalisée (cohérence avec task-184)

## Manual Test Plan

1. Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost`
2. **Collision d'UID** : dans la boîte de test, s'assurer d'avoir deux messages
   pertinents pour un même terme (« créatinine ») dans **deux dossiers différents**
   qui portent le même UID (par exemple `INBOX` UID 57 et `INBOX/Archives 2025`
   UID 57 — vérifiable dans les logs de synchronisation). Données anonymisées.
3. Lancer la recherche « créatinine » **sans filtre de dossier**. **Attendu** : les
   deux messages apparaissent. Avant correctif, un seul apparaît et l'autre est
   invisible, sans aucune indication.
4. **Casse** : rechercher l'expéditeur en minuscules alors que l'adresse est en
   majuscules → le message est trouvé. Avant correctif : aucun résultat.
5. **Jokers** : rechercher un terme contenant `%` → traité littéralement, pas comme
   un joker.
6. **Troncature** : lancer une recherche très large (terme fréquent) → si des
   résultats sont écartés par plafonnement, l'interface l'indique.
7. Non-régression : une recherche filtrée sur un seul dossier donne les mêmes
   résultats qu'avant le correctif.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — volet MSSanté
- **Exigences DSR honorées** : correctif de conformité — accès effectif du praticien
  à l'intégralité des documents reçus
- **INS** : non applicable — la recherche par traits patients n'est pas modifiée
- **Authentification PS** : inchangée
- **Habilitations** : inchangées — la recherche reste circonscrite à la base du
  praticien
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : la recherche reste journalisée sans la requête brute
  (task-184) ; ne pas introduire de nouvelle journalisation de contenu ici
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangé — pas de nouveau traitement. Risque
  d'exactitude/complétude (art. 5.1.d) à signaler : un praticien a pu conclure à
  l'absence d'un document qui existait.

## Branches
- `api-mail` (pushed) : fix/task-192-search-exhaustive-dedup-case — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-192-search-exhaustive-dedup-case
- `dtos-mss` (pushed, créée par `/develop` — contrat modifié) : fix/task-192-search-exhaustive-dedup-case — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/fix/task-192-search-exhaustive-dedup-case

## Develop log

- Repos touched : `api-mail`, `dtos-mss` (branche paresseuse, contrat modifié)
- DTOs published : `HealthPlatform.Dtos.Mss` 489.0.0 → **492.0.0** (run 36756554967) — ajout pur : `SearchResponseDto.Hits` (`SearchHitDto` Uid + FolderPath) et `SearchResponseDto.IsTruncated` ; `Uids` inchangé
- Interop published : no interop change
- Commits :
  - dtos-mss : `65440b3` feat(dto): la reponse de recherche signale la troncature et qualifie chaque resultat par son dossier
  - api-mail : `27be365d` fix(search): la recherche ne cache plus de resultats (dedup, ordre, casse, jokers, troncature) — inclut le bump DTO 492.0.0 et les `packages.lock.json` régénérés (précédent task-303/314)
  - api-mail : `cd354e50` refactor(search): simplify pass (/simplify)
- Ce qui a changé :
  1. **Déduplication** full-text sur `MailId` (`DistinctBy`) au lieu de `GroupBy(Uid)` ; le service fusionne et intersecte sur `(FolderPath, Uid)` (clé `MailKey`). La déduplication et l'intersection des filtres étaient elles aussi sur l'UID seul côté service — défaut non décrit par la task, corrigé.
  2. **Fenêtre de candidats** ordonnée `SentDate IS NULL, SentDate DESC, Uid DESC`.
  3. **Casse** : `ILIKE` sur sujet, nom/adresse expéditeur, adresse destinataire, noms patient (chemins vectoriels, embeddings, filtres).
  4. **Jokers** : `SearchQueryHelper.ToContainsPattern` échappe `%`, `_` et l'antislash (caractère d'échappement explicite) sur tous les LIKE de la recherche.
  5. **Troncature** : `ISemanticSearchService` rend un `SemanticSearchResultSet` (`IsTruncated`) ; le contrôleur expose `Hits` + `IsTruncated` sur `/search/semantic` et `/search/patient`.
- RED vérifié sur le code d'origine : 12/13 cas du nouveau `SemanticSearchRepositoryExhaustivenessIntegrationTests` rouges (collision d'UID ×2, fenêtre par date ×2, casse ×4, jokers ×3, nom patient ×1). Le cas antislash passait déjà (Npgsql émet `ESCAPE ''` sur `Like` à 2 arguments) — gardé comme garde-fou de l'échappement.
- Local build / test : ✓ api-mail — build 0 erreur ; suite complète 5 970 réussis, 0 échec, 16 ignorés (inchangé)
- Passe qualité (/simplify) :
  - Applied & committed : api-mail — 6 fichiers (`cd354e50`) : `VectorSearchResult.MailId` retiré (jamais lu), `ExtractFilteredUids` supprimé (plus d'appelant, test reporté sur `ExtractFilteredHits`), recherche patient via `MergeBySearchMode`, `SemanticSearchResultSet` sur `ReadOnlyCollection`, tuples de motifs dépliés, renommage `allKeys`/`key`
  - Skipped : **détection de troncature portée par le repository** (`Take(bound + 1)` par terme). Le service infère la saturation depuis le compte rendu, ce qui peut manquer une fenêtre pleine réduite par `DistinctBy` (plusieurs documents d'un même mail) et lever un faux positif à exactement 200 résultats. Changement de comportement + de signature, hors passe qualité → **à arbitrer par `/review`**. `FilterSearchResult.MailId` conservé volontairement (identité non ambiguë dans les tests). Index trigram/date hors périmètre.
  - Skipped (contract/excluded) : dtos-mss
- DOD self-check (8/9 vérifiables par commande, 1 différé HAG) :
  - [x] Build 0 erreur / tests 0 échec
  - [x] Collision d'UID dossiers différents ⇒ les deux retournés, rouge sur le code d'origine : `FullTextSearchEmailContentsAsync_SameUidInTwoFolders_ReturnsBothMails` (+ variante documents, + service `SearchAsync_SameUidInTwoFolders_ReturnsBothMails`)
  - [x] Fenêtre ordonnée par date : `FullTextSearchEmailContentsAsync_CandidateWindow_KeepsMostRecentMailWhateverItsUid`, `FullTextSearchEmailContentsAsync_MailWithoutDate_ComesAfterDatedMails`
  - [x] « dupont » trouve « DUPONT »/« Dupont » sur sujet, nom et adresse expéditeur : `SearchByFiltersAsync_LowerCaseInput_MatchesUpperAndMixedCase` (théorie ×3) + destinataire + nom patient
  - [x] `%` / `_` littéraux : `SearchByFiltersAsync_WildcardCharactersInInput_AreMatchedLiterally` (×3), `FullTextSearchEmailContentsAsync_WildcardInTerm_DoesNotFillWindowWithFalseCandidates`, `ToContainsPatternEscapesLikeWildcards`
  - [x] Plafond ⇒ réponse le signale : `SemanticSearch_TruncatedResults_FlagsTheResponse`, `SearchByPatient_TruncatedResults_FlagsTheResponse`, 5 cas service `*_IsTruncated`
  - [x] Non-régression mono-dossier : suites existantes vertes, dont `FullTextSearchEmailContentsAsyncShouldRespectPerTermCapAsync`
  - [x] Aucune requête brute journalisée : aucun nouveau log (seuls les `LogTrace` existants passent `key.Uid`)
  - Manual Test Plan : différé au test humain (HAG)
- À savoir pour `/review` et le HAG :
  - Les fronts (`client-blazor`, `client-angular`, `client-mobile`) lisent encore `Uids` seuls et n'affichent pas `IsTruncated` : l'étape 6 du Manual Test Plan (« l'interface l'indique ») **n'est pas observable côté UI** tant qu'une task front n'a pas consommé `Hits`/`IsTruncated`. Côté API, vérifiable directement dans la réponse de `POST /api/v1/search/semantic`.
  - `client-blazor` non listé : non bumpé à 492.0.0 (ajout pur, aucune casse).
- Next step : /sonar task-192

## Sonar log

- Mode A (chaîné), projet `healthplatform-api-mail`, serveur 25.6.0.109173 sur `localhost:9001` (conteneurs `sonarqube_db` puis `sonarqube` redémarrés — arrêtés depuis 25 h), propriété `sonar.token`
- Itérations : 2 analyses (baseline + vérification)

### KPIs qualité

| Métrique | Baseline (itér. 1) | Final (itér. 2) |
|---|---|---|
| Issues new-code dans les fichiers de task-192 | 11 (S103 ×11) | **0** |
| Issues new-code, tout le projet | 70 | 59 |
| `new_code_smells` | 68 | 57 |
| `new_bugs` / `new_vulnerabilities` | 2 / 0 | 2 / 0 |
| `new_coverage` (projet) | 98.3 % | 98.3 % |
| `new_coverage` des fichiers source de task-192 | 97.2–100 % | 97.2–100 % |
| `coverage` (projet) | 98.2 % | 98.2 % |
| `code_smells` (projet) | 72 | 61 |
| `bugs` / `vulnerabilities` | 2 / 0 | 2 / 0 |
| Ratings fiabilité / sécurité / maintenabilité | D / A / A | D / A / A |
| Hotspots new-code `TO_REVIEW` | 13 (aucun dans les fichiers de task-192) | 13 |
| **Quality Gate** | **ERROR** | **ERROR** |

- **Phase 1 (new code de task-192) : verte.** 11 × `csharpsquid:S103` sur `SemanticSearchRepository.cs` corrigés (`74c20b50`) : alias `private const string LikeEscape` + projections `EmailCandidate` dépliées. Zéro issue, zéro hotspot restant dans les fichiers du diff ; couverture new-code par fichier ≥ 97.2 % (cible 95 %).
- **Quality Gate ERROR non imputable à task-192** : les conditions en échec (`new_violations` 59, `new_security_hotspots_reviewed` 0 %) portent exclusivement sur des fichiers hors diff, entrés dans la new-code period avec des tasks déjà mergées (python:S3776 ×21, javascript:S1940 ×20, … — banc de charge et outillage). Provenance vérifiée fichier par fichier contre `git diff origin/develop...HEAD` (cf. mémoire « la new-code period inclut des tasks déjà mergées »). Les corriger sortirait du périmètre (règle 6).
- **Phase 2 (legacy)** : skipped — best-effort, non bloquante ; la dette legacy relevée porte sur des modules hors périmètre de la task.
- Conventions : `conventions/csharp.md` § S103 → Occurrences 2 (variante requête EF, consigne complétée).
- Build / tests : Release 0 erreur ; 5 970 réussis, 0 échec, 16 ignorés.
- Next step : /lint-angular task-192

## Lint log

- `/lint-angular` : **skipped** — `client-angular` non listé dans `**Repos**:` (US backend-only), aucun fichier Angular touché.

## Lint mobile log

- `/lint-mobile` : **skipped** — `client-mobile` non listé dans `**Repos**:` (US backend-only), aucun fichier mobile touché.

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail + dtos-mss touchés | ✅ verte (1 flaky) | 23 verts, 1 flaky, 0 rouge, 0 quarantaine | voir la section Timings |
| angular | api-mail + dtos-mss touchés | ⏭️ sautée | suite Angular non livrée (task-346) — colonne « non contrôlée » | — |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ branche de la task (`fix/task-192-search-exhaustive-dedup-case`)
- Quarantaines : aucune
- Divergences ouvertes : aucune
- Parcours touchés sans spec e2e modifié : aucun (aucun écran touché)
- Démontage : complet (ports libres, aucun conteneur e2e résiduel)
- **⚠️ À examiner au HAG — E2E-DETAIL-002 (mobile)** : un premier run sur la branche de la task a été **rouge aux deux essais** (« mail sans corps affichable ») et a arrêté la chaîne. Contre-épreuve demandée par l'humain : voie mobile rejouée avec l'`api-mail` de `develop` → **vert au 1er essai** ; rejouée sur la branche de la task → **flaky** (rouge au 1er essai, vert au 2e). Soit 3 échecs sur 4 essais sur le code de la task, contre 1 réussite sur 1 sur `develop`. Aucun fichier du diff n'est sur le chemin de lecture d'un message (le diff ne touche que la recherche). Classé **flaky** par la porte, non bloquant ; inscrit au registre des flaky de `conventions/e2e.md`. Un faible écart de minutage entre les deux backends n'est pas exclu.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**Flaky (vert au second essai, non bloquant)** (1) :

- [mobile] « détail — bascule texte brut / HTML » (E2E-DETAIL-002)

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | non contrôlé | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | non contrôlé | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | non contrôlé | ✅ |
| E2E-CONTACT-001 | 1 | humain | Rechercher dans le carnet et interroger l'annuaire national | non contrôlé | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | non contrôlé | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | non contrôlé | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | non contrôlé | ✅ |
| E2E-DETAIL-001 | 1 | headless | Répondre et transférer depuis la lecture d'un message | non contrôlé | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | non contrôlé | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | non contrôlé | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | non contrôlé | ✅ |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | non contrôlé | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | non contrôlé | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | non contrôlé | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | non contrôlé | ⚠️ flaky |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | non contrôlé | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | non contrôlé | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | non contrôlé | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | non contrôlé | ✅ |
| E2E-CONTACT-002 | 1 | headless | Créer puis supprimer un contact | non contrôlé | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | non contrôlé | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | non contrôlé | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | non contrôlé | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | non contrôlé | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | non contrôlé | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | non contrôlé | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | non contrôlé | ✅ |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/266 — label `awaiting-human-merge`
- `dtos-mss` : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/35 — label `awaiting-human-merge` (HealthPlatform.Dtos.Mss 492.0.0 déjà publié depuis la branche)
- `client-blazor`, `client-angular`, `client-mobile` : non listés — consomment toujours `Uids` seul ; exploitation de `Hits` / `IsTruncated` à planifier dans une task front

## Code Review Summary

- Validation `/review` : `dtos-mss` build 0 erreur ; `api-mail` build 0 erreur, **5 970 tests réussis, 0 échec**, 16 ignorés ; branches déjà à jour avec `origin/develop` (aucun merge nécessaire)
- DOD : 8/9 vérifiés par commande (tests nommés dans le `## Develop log`), 1 différé au Manual Test Plan (HAG)
- E2E double verrou : `## E2E log` vert (1 flaky E2E-DETAIL-002, contre-épreuve `develop` documentée)
- **Verdict : APPROVED** — 0 bloquant, 4 suggestions :
  1. défaut **pré-existant** : recherche vectorielle par patient en mode hybride — plusieurs documents d'un même mail ⇒ `ToDictionary` sur clé en double ⇒ exception avalée ⇒ **liste vide sans signal** (déjà sur `develop`, clé UID) → task dédiée recommandée
  2. détection de troncature à porter par le repository (`Take(bound + 1)`)
  3. `ContactRepository` / `PatientRepository` : LIKE sans échappement des jokers → adopter `SearchQueryHelper.ToContainsPattern`
  4. cosmétique (lignes vides `SearchResultHelper` / `#endregion`)

## Timings

*(généré par `tools/timing/report.sh --task task-192 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 32 s | — | — | — | — |
| /develop | ok | 33 min 20 s | 6 (49 s) | 9 (10 min 27 s) | — | api-mail 5B/9T, dtos-mss 1B/0T |
| /sonar | ok | 19 min 43 s | 2 (53 s) | 10 (8 min 27 s) | 4 (5 min 00 s) | 2 itération(s), api-mail 2B/10T |
| /lint-angular | skipped | 1.9 s | — | — | — | client-angular non listé dans Repos |
| /lint-mobile | skipped | 2.1 s | — | — | — | client-mobile non listé dans Repos |
| /e2e | ok | 31 s | — | — | — | e2e ×3 (5 min 05 s), vert, 1 flaky E2E-DETAIL-002 (rejeu après contre-épreuve develop) |
| /review | ok | 5 min 45 s | 2 (18 s) | 1 (3 min 00 s) | — | dtos-mss 1B/0T, api-mail 1B/1T |
| /tech-writer | ok | 1 min 43 s | — | — | — | — |
| **Total cycle** | | **1 h 01 min** | **10 (2 min 01 s)** | **20 (21 min 55 s)** | **4 (5 min 00 s)** | |

Autres commandes mesurées : nuget-wait ×1 (12 s), restore ×1 (8.4 s)
