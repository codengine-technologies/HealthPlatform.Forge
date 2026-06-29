# todo-task-119.md — Recherche avancée `mail-search` + historique de recherche (mobile, angular, backend)

**Repos**: api-mail, dtos-mss, client-angular, client-mobile
**Dependencies**: done-task-110
**Epic**: E014

## Objective
Refondre **structurellement** la recherche de messages `mail-search` et y
adosser un **historique de recherche** partagé, persisté côté backend dans le
cache Redis. **Changement fonctionnel assumé** (l'ancien périmètre « restyling
UI sans changement fonctionnel » est caduc).

### client-mobile (référence Stitch `mail-search`, socle `done-task-110`)
Au niveau de la page tabs/messages, retirer la zone de recherche inline et la
remplacer par une **icône loupe** placée à droite des filtres (Non lus, Pièces
jointes, etc.). Un clic sur la loupe ouvre une **page dédiée de recherche
avancée** correspondant à l'écran Stitch `mail-search`.

Cet écran porte les critères de recherche **et** le résultat. La liste de
résultats **réutilise le composant existant `mail-list`**. La sélection d'un
email dans les résultats bascule dans la **vue détail** ; au retour depuis un
résultat de recherche, on revient **dans les résultats sans perdre le contexte
de recherche** (critères + résultats restaurés).

La page affiche l'**historique des recherches précédentes** (rechargé depuis le
nouvel endpoint backend) ; sélectionner une entrée d'historique réexécute la
recherche correspondante. L'écran Stitch `mail-search` prévoit une action
**« effacer l'historique »** qui vide l'historique du praticien (appel de
l'endpoint d'effacement backend, puis vidage de la liste affichée).

### client-angular
Mettre à jour le module MSS pour **supporter également l'historique de
recherche** : consommer le même endpoint backend (historique + persistance de
la query), afficher les recherches précédentes, permettre de les rejouer **et
d'effacer l'historique**. Périmètre minimal aligné sur le contrat backend ; pas
de refonte Stitch côté Angular.

### api-mail + dtos-mss
- **Nouveau DTO** d'historique de recherche dans `dtos-mss` (entrée d'historique
  + payload de réponse de l'endpoint).
- **Nouvel endpoint** backend exposant l'historique des recherches précédentes
  du praticien, lu depuis le cache Redis.
- À chaque recherche déclenchée, la **query est mise en cache** Redis avec un
  **TTL de 7 jours**.
- **Endpoint d'effacement** de l'historique : supprime la clé de cache Redis du
  praticien (`ICacheService.Remove`). Exposé côté UI par l'action « effacer
  l'historique » présente dans l'écran Stitch `mail-search`.
- **Scope praticien** : l'**email du praticien fait partie de la clé de cache**
  (ex. `mss:search-history:{practitionerEmail}`), garantissant un historique
  strictement isolé par praticien.
- Gestion d'erreurs via `GlobalExceptionHandler` / `ProblemDetails` (règle 12) —
  aucun `try/catch` ad hoc ni `StatusCode(500, ...)` dans l'action.

## Référence Stitch
- **Réutiliser** l'écran Stitch `mail-search` (correspondance exacte).
- Étape design : `/stitch-design task-119`. Stitch = référence, pas du code.

## Parité des critères de filtre (client-angular → client-mobile) — 100 %
Le **fonctionnel de recherche doit être à 100 %** : tous les critères de
`client-angular` doivent être reportés dans `client-mobile`. Le modèle DTO
mobile (`core/models/search.model.ts`) est **déjà identique** à celui d'Angular
— le backend supporte donc tout ; l'écart est uniquement dans la logique du
composant mobile (qui ne couvre aujourd'hui qu'un sous-ensemble).

Référence Angular : `libs/mss/src/features/mail/components/mail-search/
mail-search.component.ts` (`buildRequest` / `buildFilters` / `buildFieldFilters`
/ `computeDateFrom`).

| Critère | Mapping DTO | État mobile actuel |
|---|---|---|
| Texte `query` | `query` | ✅ présent |
| Non lus | `statusFilters.isRead=false` | ✅ présent |
| **Important** | `statusFilters.isImportant=true` | ❌ **à ajouter** |
| Pièces jointes | `contentFilters.hasAttachments` | ✅ présent |
| Tous documents médicaux | `contentFilters.hasMedicalDocuments` | ✅ présent |
| Biologie | `contentFilters.hasBiologyResults` | ✅ présent |
| **Type de document (14 types)** | `contentFilters.medicalDocumentType` | ❌ **à ajouter** |
| **Plage de dates (1/7/30/90 j)** | `dateFilters.sentDateFrom` (ISO, now − N j) | ❌ **à ajouter** |
| **Expéditeur (avancé)** | `fieldFilters.fromAddress` | ❌ **à ajouter** |
| **Destinataire (avancé)** | `fieldFilters.recipientAddress` | ❌ **à ajouter** |
| **Sujet (avancé)** | `fieldFilters.subject` | ❌ **à ajouter** |
| `minSimilarity` (réglages user) | `minSimilarity` | ❌ (codé en dur `0.1` — lire les réglages) |
| Constantes | `searchType=3`, `searchMode=3`, `maxResults=50` | ✅ aligné |

Les 14 types de document (chips + sélecteur avancé côté Angular) :
`Consultation, Imagerie, Prescription (« Ordonnances »), Hospitalisation,
Synth (« Synthèse »), Vaccination, Operatoire (« Chirurgie »), Urgences,
Anatomopathologie, Genetique, Pharmacie, Procedure, HistoirePhysique, Bio`.
Les types et plages de dates sont **mutuellement exclusifs** (re-clic = désélection),
comme dans Angular.

## Alignement de nommage des composants (angular ↔ mobile)
Pour faciliter le travail de l'IA, les composants équivalents portent un **nom
identique** dans les deux repos (même nom de dossier/sélecteur, préfixe `mss-`).
Le domaine `mail-*` est déjà aligné (`mail-list`, `mail-detail`, `mail-header`,
`mail-search`, `mail-folder-list`, etc.).

- Le composant de **critères de recherche** reste `mail-search` dans les deux
  repos (sélecteur `mss-mail-search`).
- Tout nouveau sous-composant **historique de recherche** porte le **même nom
  des deux côtés** : `mail-search-history` (sélecteur `mss-mail-search-history`).
  Si Angular n'a pas encore ce composant, le créer sous ce nom (pas un nom
  divergent type `search-history-list`).
- La liste de résultats réutilise le composant existant `mail-list` (déjà
  aligné dans les deux repos) — ne pas créer de variante.
- La page dédiée mobile (spécifique à Ionic) peut être une page `mail-search`
  hébergeant le composant `mail-search` + `mail-search-history` + `mail-list`.

## Definition of Done

### Backend (`api-mail` + `dtos-mss`)
- [ ] Build passe (`dotnet build HealthPlatform.Api.Mail.sln`, 0 erreur)
- [ ] Tests passent (`dotnet test HealthPlatform.Api.Mail.sln`, 0 échec)
- [ ] Nouveau DTO d'historique de recherche dans `dtos-mss` (entrée + réponse)
- [ ] DTO publié en NuGet et consommateurs .NET bumpés (`/publish-dtos`) si le
      contrat change
- [ ] Nouvel endpoint « historique de recherche » (lecture depuis Redis)
- [ ] Query mise en cache Redis à chaque recherche, **TTL 7 jours**
- [ ] Endpoint d'**effacement** de l'historique (`ICacheService.Remove` de la
      clé praticien)
- [ ] Clé de cache scopée praticien — l'**email du praticien est dans la clé**
- [ ] Test d'intégration des endpoints (lecture + effacement : happy path +
      1 mode d'échec) — règle 1b
- [ ] Tests unitaires du service d'historique/cache (>= 1 test par méthode
      publique / branche) — règle 1c
- [ ] Erreurs en `ProblemDetails` via `GlobalExceptionHandler` — règle 12

### client-mobile
- [ ] Build passe (`npm ci && npm run build`, 0 erreur)
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`, 0 échec)
- [ ] Zone de recherche inline retirée de la page tabs/messages
- [ ] Icône loupe ajoutée à droite des filtres ; clic → page de recherche dédiée
- [ ] Page de recherche alignée sur l'écran Stitch `mail-search`
- [ ] **Parité filtres 100 %** : `important`, `medicalDocumentType` (14 types),
      plage de dates (1/7/30/90 j → `sentDateFrom`), `fromAddress`,
      `recipientAddress`, `subject` ajoutés (cf. matrice de parité)
- [ ] `minSimilarity` lu depuis les réglages utilisateur (plus de `0.1` en dur)
- [ ] Types de document et plages de dates mutuellement exclusifs (parité Angular)
- [ ] Résultats rendus via le composant existant `mail-list` (réutilisation)
- [ ] Sélection d'un résultat → vue détail ; retour → résultats **avec contexte
      de recherche conservé** (critères + résultats)
- [ ] Historique de recherche affiché et rejouable (depuis l'endpoint backend)
- [ ] Action « effacer l'historique » (écran Stitch) → appel endpoint
      d'effacement + vidage de la liste
- [ ] Composant historique nommé `mail-search-history` (aligné avec Angular)
- [ ] Tokens du socle réutilisés — aucune valeur de design en dur
- [ ] `data-testid` préservés/complétés (loupe, page recherche, entrées
      d'historique)
- [ ] Tests unitaires de la page de recherche (rendu + interaction primaire)
- [ ] Comparaison visuelle avec le screenshot Stitch consignée

### client-angular
- [ ] Build passe (`npm ci && npm run build`, 0 erreur)
- [ ] Tests passent (`npm test`, 0 échec)
- [ ] Module MSS consomme l'endpoint d'historique de recherche
- [ ] Recherches précédentes affichées et rejouables
- [ ] Action « effacer l'historique » → appel endpoint d'effacement + vidage
- [ ] Composant historique nommé `mail-search-history` (aligné avec mobile)
- [ ] Tests unitaires de la logique d'historique ajoutée

### Alignement cross-repo
- [ ] Composants équivalents portent un nom identique (`mail-search`,
      `mail-search-history`, `mail-list`) dans angular et mobile

## Manual Test Plan

### client-mobile
- Lancer le mobile, ouvrir la page tabs/messages.
- Vérifier que la zone de recherche inline a disparu et qu'une **icône loupe**
  apparaît à droite des filtres.
- Cliquer la loupe → la **page de recherche dédiée** s'ouvre (design Stitch
  `mail-search`).
- Saisir des critères, lancer une recherche → résultats rendus via `mail-list`.
- Ouvrir un résultat → vue détail ; revenir → **les résultats et les critères
  sont conservés** (pas de reset).
- Vérifier que l'**historique des recherches précédentes** s'affiche ; cliquer
  une entrée → la recherche est rejouée.
- Cliquer **« effacer l'historique »** → la liste se vide ; après rechargement,
  l'historique reste vide.
- Comparer à la maquette Stitch `mail-search`.

### client-angular
- Lancer le client Angular, ouvrir la messagerie MSS.
- Lancer une recherche, vérifier les résultats.
- Vérifier que les **recherches précédentes** s'affichent et sont rejouables.

### Backend
- Déclencher une recherche, vérifier via Redis que la query est mise en cache
  sous une clé contenant l'email du praticien, avec un TTL ~7 jours.
- Appeler l'endpoint d'effacement → vérifier que la clé praticien est supprimée
  dans Redis.
- Avec un second praticien, vérifier l'**isolation** de l'historique (clés
  distinctes, aucun partage ; effacer l'un n'impacte pas l'autre).

## Conformité santé / Ségur / ANS
- **Couloir / Vague Ségur** : hors couloir / hors Ségur.
- **RGPD / PGSSI-S / HDS** : **applicable** — l'historique de recherche persiste
  des requêtes de praticien (donnée personnelle, pouvant contenir des termes
  cliniques ou un nom patient) dans Redis pendant 7 jours.
  - **Minimisation** : ne stocker que la query/les critères nécessaires au
    rejeu ; **ne jamais** stocker d'INS/NIR ni de contenu MSSanté en clair.
  - **Scope strict par praticien** : email du praticien dans la clé de cache,
    aucun historique partagé entre praticiens.
  - **TTL 7 jours** : rétention bornée et justifiée (commodité de rejeu).
- **Habilitations** : l'endpoint d'historique ne renvoie que l'historique du
  praticien authentifié (pas d'accès croisé).
- **UI** : ne jamais exposer d'INS/contenu MSSanté en clair dans l'historique
  affiché.

## Branches
- `api-mail` (pushed) : feat/task-119-mail-search-history — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-119-mail-search-history
- `dtos-mss` (pushed) : feat/task-119-mail-search-history — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-119-mail-search-history
- `client-mobile` (pushed) : feat/task-119-mail-search-history — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-119-mail-search-history
- `client-angular` (code-only) : forge writes code on the branch currently checked out in `Client/Angular/` (snapshot at /start : `feature/nova-rewriting-mss`) — humain gère branche, commit, push, PR TFS

## Stitch design log
- Projet Stitch `client-mobile` (id `10088502293310567548`, MOBILE).
- Écran **réutilisé** (correspondance exacte) : `mail-search`
  (id `fd767eca895f41b1b30a8bc932cf40cf`).
  - Screenshot : https://lh3.googleusercontent.com/aida/AP1WRLvwYlqIffGX9KuY68ACIWD_Stw1Dw8iAfIrqwVSBonv55XLSLYHdPZtH3Fgb3QtgBXzbEwyI0RpU0J3eSaaXHJ7TREDDNpcQ8z-KDvJeOMGM2chA-vJW5La1x299w_psx_l8XKbYwLpgYlw2zSGfrd4_48iAZsjTf90MH5MguF6vDYtz-pkTlY0I0gWkG5cPv_QmReNfTU3Tx9FQVut7HPOeG_oksQySjr1dVnG9qzYlvhBWjEmPyrJKmti
  - HTML ref (id de fichier) : `projects/10088502293310567548/files/13857403550330241348`
- Intention de layout traduite en Ionic (référence, pas du code collé) :
  header « MSSanté - Recherche » + retour ; barre de recherche « Rechercher un
  email… » ; section **« Recherches récentes »** avec action **« Effacer »** et
  lignes historique (icône `history` + libellé requête + temps relatif + flèche
  de rejeu `north_west`) ; pied « Recherche sécurisée de bout en bout ».
- Le composant critères = `mss-mail-search`, l'historique = `mss-mail-search-history`,
  les résultats = `mss-mail-list` (réutilisé). Tokens du socle E014 réutilisés.

## Develop log
- **Repos touchés** : `dtos-mss`, `api-mail`, `client-mobile` (pushés), `client-angular` (code-only).
- **DTOs publiés** : HealthPlatform.Dtos.Mss `335.0.0 → 337.0.0` (SearchHistoryEntryDto + SearchHistoryResponseDto). Consommateur `api-mail` bumpé.
- **Interop publié** : aucun changement interop.
- **Commits poussés** :
  - dtos-mss : `7ff425e` feat(dto): add search history DTOs
  - api-mail : `eb3d707` feat(search): practitioner search history (Redis, 7-day TTL)
  - client-mobile : `260a201` feat(mobile): dedicated mail-search page + search history
- **client-angular (code-only, non commité — l'humain gère git/PR TFS)**, branche `feature/nova-rewriting-mss` :
  - `libs/mss/src/core/models/search.model.ts` — DTOs historique
  - `libs/mss/src/core/services/mss-api.service.ts` — getSearchHistory / clearSearchHistory
  - `libs/mss/src/features/mail/components/mail-search/mail-search.component.ts` — `replay()` + inferDateRange
  - `libs/mss/src/features/mail/components/mail-search-history/` (nouveau composant `mss-mail-search-history` + spec)
  - `libs/mss/src/features/mail/components/mail-list/` — hôte (viewChild + onReplaySearch + stub spec)
- **Vérifs locales** :
  - api-mail : build 0 erreur ; tests `application` 1767✓, `api` 523✓, `integration` SearchHistory 3✓.
  - client-mobile : `npm run build` ✓ ; `npm test` headless 148✓.
  - client-angular : AOT dev build `nx build mss` ✓ ; `nx test mss-lib` 299✓.
    - **2 échecs PRÉ-EXISTANTS** hors scope task-119 dans `mail-list.component.spec.ts`
      (bloc `requestSelectByUid$ subscription (task-036)`) : `new MailListComponent()`
      lève `NG0201 MailDestinationRefreshService` car ce provider manque dans ce bloc
      de test **déjà au HEAD** de la branche `feature/nova-rewriting-mss` (rewriting en cours
      côté humain). Indépendant de cette US ; à corriger sur la branche Angular par l'humain.
- **DOD** : voir cases ci-dessus ; observables (rendu Stitch, Redis TTL, isolation praticien) déférés au test humain (HAG).
- **Next step** : /forge-simplify task-119

## Simplify log
- Repos passed : api-mail, client-mobile (pushable), client-angular (code-only).
- Applied & committed : none — fresh code already reuse-clean (réutilise
  `mss-mail-list`, `SafeCacheExtensions`, `extractProblemDetail`, tokens E014 ;
  helpers `Has*Filter` / `inferDateRange` extraits ; aucun mort/duplication intra-repo).
- Applied (code-only, uncommitted) : none.
- No change : api-mail, client-mobile, client-angular.
- Rolled back (validation RED) : none.
- Skipped (contract/excluded) : dtos-mss (porteur de contrat), interop-cda, devops, psc-proxy-*.
- Build / tests : déjà verts (cf. Develop log) ; aucune édition à re-valider.
- Next step : /sonar task-119 (api-mail touché).

## Sonar log
- Skipped (best-effort) : SonarQube non provisionné — `SONAR_TOKEN` absent et
  serveur `localhost:9000` injoignable (HTTP 000). Conforme à la posture
  connue (infra non provisionnée). Aucun blocage ; chaîne poursuivie.
- Next step : /lint-angular task-119 (client-angular touché).

## Lint log (client-angular, code-only)
- Scope : `mss-lib` (module MSS). Mode A chaîné.
- Baseline : 36 problèmes (3 erreurs, 33 warnings) — 3 erreurs fixables.
- Itération 1 (`nx lint mss-lib --fix`) : 3 erreurs auto-corrigées → **0 erreur**
  restante (warnings JSDoc/max-lines pré-existants conservés, best-effort).
- Re-validation : AOT dev build `nx build mss` ✓ après reformat.
- Code-only : éditions laissées non commitées (l'humain commit/push/PR TFS).
  Le `--fix` a aussi reformaté un fichier MSS pré-existant
  (`core/utils/problem-details.utils.ts`) — dans le périmètre MSS, conservé.
- Next step : /lint-mobile task-119 (client-mobile touché).

## Lint mobile log (client-mobile)
- Baseline `npm run lint` (ng lint) : **All files pass linting** — 0 erreur.
- Aucune correction nécessaire ; aucun commit. Skip clean.
- Next step : /review task-119.

## PRs
- `dtos-mss` (pushed) : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/25 — label `awaiting-human-merge`
- `api-mail` (pushed) : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/112 — label `awaiting-human-merge`
- `client-mobile` (pushed) : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/22 — label `awaiting-human-merge`
- `client-angular` (code-only) : l'humain gère commit/push TFS et ouverture de PR. Fichiers modifiés (non commités, branche `feature/nova-rewriting-mss`) :
  - front/apps/mss/src/environments/environment.ts
  - front/libs/mss/src/core/models/search.model.ts
  - front/libs/mss/src/core/services/mss-api.service.ts
  - front/libs/mss/src/core/utils/problem-details.utils.ts
  - front/libs/mss/src/features/mail/components/mail-list/mail-list.component.html
  - front/libs/mss/src/features/mail/components/mail-list/mail-list.component.spec.ts
  - front/libs/mss/src/features/mail/components/mail-list/mail-list.component.ts
  - front/libs/mss/src/features/mail/components/mail-search/mail-search.component.ts
  (note : `apps/mss/src/environments/environment.ts` est un WIP humain pré-existant, hors task-119.)

## Code Review Summary
✅ **APPROVED** — 0 blocant.
- dtos-mss : DTOs additifs conformes.
- api-mail : scope praticien isolé (email dans la clé), TTL 7 j (deux fenêtres), minimisation INS, résilience cache, RFC 7807 (règle 12) ; tests unit+controller+intégration verts (build 0 err, 1767+523+3).
- client-mobile : réutilise `mail-list`, parité filtres 100 %, minSimilarity réglages, contexte conservé ; build ✓, 148 tests ✓, lint 0 err.
- client-angular (code-only) : replay + `mss-mail-search-history` + endpoints ; AOT build ✓, 299 tests ✓ (2 échecs **pré-existants** hors scope dans `mail-list.component.spec` bloc task-036 — provider `MailDestinationRefreshService` manquant déjà au HEAD).
- US-complete (règle 11) : US fonctionnellement complète end-to-end (backend + mobile mergeable ; angular géré humain). Label `awaiting-human-merge`.

## Merged
- Date : 2026-06-25 (human `/merge --i-tested`, HAG rule 10 satisfaite).
- Squash-merge sur `develop` :
  - `dtos-mss` : `ea0c319` (PR #25 fermée) — CI develop ✓ (run 28163344317)
  - `api-mail` : `a07b71c` (PR #112 fermée) — CI develop ✓ (run 28163356642)
  - `client-mobile` : `51c0be8` (PR #22 fermée) — pas de workflow CI develop sur ce repo
- Remote branches `feat/task-119-mail-search-history` supprimées ; branches locales conservées.
- `client-angular` : code-only — géré manuellement par l'humain (hors scope /merge).
