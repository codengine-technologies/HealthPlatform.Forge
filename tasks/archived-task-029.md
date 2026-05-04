# todo-task-029.md — Parité recherche Angular ↔ Blazor (élagage volontaire)

**Repos**: client-angular
**Single frontend**: true
**Dependencies**: —
**Epic**: E009

## Objectif

Aligner la `mail-search` Angular sur la richesse fonctionnelle de la
`SearchMailComponent.razor` Blazor. Aujourd'hui Angular n'expose qu'un input
texte qui appelle le backend en sémantique pur (`searchType=3`,
`searchMode=3`) sans aucun filtre. Blazor offre un dropdown sous l'input
avec quick-filters statut, chips de contenu médical, plages de dates,
panel de recherche avancée. **Cible** : Angular reproduit fonctionnellement
le dropdown Blazor avec une UX visuellement équivalente, en profitant de
l'occasion pour **dégraisser** la liste des chips médicaux (14 → 6) — les
9 types restants restent accessibles via le sélecteur « Type de document »
de la recherche avancée.

**Aucun changement backend / DTO C# / contrat.** Les endpoints
`POST /api/v1/search/semantic` et `POST /api/v1/search/patient` couvrent
déjà les filtres ; le `SearchRequestDto` côté backend les expose.

> **Note** : cette US prépare task-030 qui redesigne ensuite le surface UX
> en panneau latéral type Outlook (les deux frontends en miroir). Task-029
> ferme l'écart de **couverture fonctionnelle** ; task-030 remet en cause
> la **forme** (dropdown → panneau). La séquence est volontaire : on livre
> d'abord la parité, puis la refonte.

## Périmètre — critères à porter

### QuickFilters (3 chips, parité Blazor)

- Non lus (`StatusFilters.IsRead = false`)
- Importants / favoris (`StatusFilters.IsImportant = true`)
- Pièces jointes (`ContentFilters.HasAttachments = true`)

### Contenu médical (6 chips — élagage PO 14 → 6)

- **Tous les documents** (`ContentFilters.HasMedicalDocuments = true`)
- **Biologie** (`ContentFilters.HasBiologyResults = true`)
- **Consultation** (`AdvancedFilters.MedicalDocumentType = "Consultation"`)
- **Imagerie** (`AdvancedFilters.MedicalDocumentType = "Imagerie"`)
- **Prescription** (`AdvancedFilters.MedicalDocumentType = "Prescription"`)
- **Hospitalisation** (`AdvancedFilters.MedicalDocumentType = "Hospitalisation"`)

**Élagués des chips** (mais restent accessibles via le sélecteur « Type de
document » de la recherche avancée — point suivant) : Synthèse, Vaccination,
Opératoire, Urgences, Anatomopathologie, Génétique, Pharmacie, Procédure,
HistoirePhysique. Aucune perte fonctionnelle, juste une réduction de la
densité visuelle du dropdown.

### Plage de dates (4 chips, parité Blazor)

- Aujourd'hui (1 jour)
- 7 derniers jours
- 30 derniers jours
- 3 derniers mois (90 jours)

Implémenté via `AdvancedFilters.DateFrom` calculé depuis `DateTime.Now`
côté frontend.

### Recherche avancée (panel, parité Blazor)

Bouton « Recherche avancée » dans le dropdown qui bascule vers un panel
contenant :

- **De** (`AdvancedFilters.FromAddress`) — input texte
- **À / CC** (`AdvancedFilters.RecipientAddress`) — input texte
- **Objet** (`AdvancedFilters.Subject`) — input texte
- **Type de document** (`AdvancedFilters.MedicalDocumentType`) — sélecteur
  exposant les **14 types** d'origine (Consultation, Imagerie, Prescription,
  Hospitalisation, Synthèse, Vaccination, Opératoire, Urgences,
  Anatomopathologie, Génétique, Pharmacie, Procédure, HistoirePhysique +
  option « Aucun filtre »). C'est ici que les types élagués des chips
  redeviennent accessibles.

## Comportement attendu

### Ouverture / fermeture du dropdown

- Le dropdown s'ouvre au focus / clic sur l'input.
- Il se ferme au click extérieur (à l'extérieur de l'input ET du dropdown).
- Il se ferme aussi à `Escape`.
- Pendant qu'il est ouvert, la saisie texte ne déclenche pas la recherche
  immédiatement — la recherche est lancée à l'`Enter` ou au clic sur un
  chip / toggle.

### Application des filtres

- Cliquer sur un chip toggle son état (active / inactif). Plusieurs chips
  peuvent être actifs simultanément (intersection logique côté backend).
- Les chips de plage de dates sont **mutuellement exclusifs** (un seul actif
  à la fois) — parité Blazor.
- Les chips de contenu médical sont mutuellement exclusifs sur la dimension
  « Type de document » (un seul type sélectionnable à la fois) ; en revanche
  « Tous les documents » et « Biologie » peuvent coexister avec un type
  spécifique (parité Blazor).
- Cliquer sur un chip lance la recherche immédiatement (pas besoin
  d'`Enter`) — parité Blazor.

### Recherche

- L'`Enter` dans l'input avec ou sans texte lance la recherche en
  combinant : `query` (texte) + chips actifs + champs du panel avancé.
- Si **aucun critère n'est actif et le texte est vide**, la recherche est
  remplacée par un appel `loadEmails()` (retour à l'inbox standard).
- Le mode `searchMode` reste **3 = sémantique sur emails + documents**
  (parité Blazor) ; le mode `searchType` reste **3 = combiné**.
- Pendant le chargement, un spinner remplace l'icône loupe et l'input est
  désactivé. Bouton clear masqué tant qu'il n'y a rien à effacer.

### Bouton Clear

- Visible uniquement quand `query !== '' || filtersActive || isSearchActive`.
- Au clic : reset de l'input, désactivation de tous les chips, vidage des
  champs du panel avancé, `searchCleared.emit()` qui ramène la liste à
  l'état inbox standard.

### Compatibilité avec le mode conversation (task-027)

- Si l'utilisateur a `MailViewMode.Conversation` activé dans ses settings,
  les **résultats de recherche** doivent eux aussi être réduits aux feuilles
  de fil (parité avec l'inbox standard) — le mode est un mode d'affichage,
  pas un mode lié à l'origine des données.
- Concrètement : une fois `state.emails.set(searchResults)` appelé, le
  computed `displayedMails` (livré par task-027) prend le relais et applique
  le filtrage feuilles. Aucun travail spécifique de search — juste
  vérification que la chaîne signaux fonctionne sur les résultats.

## Périmètre détaillé

### `core/models/search.model.ts`

- Vérifier que `SearchRequestDto` expose **toutes** les propriétés suivantes
  (s'aligner sur la version C# si manquantes) :
  - `query`, `maxResults`, `minSimilarity`, `searchType`, `searchMode`,
    `folderPath` (déjà présents)
  - `statusFilters?: { isRead?: boolean; isImportant?: boolean }`
  - `contentFilters?: { hasAttachments?: boolean; hasMedicalDocuments?: boolean; hasBiologyResults?: boolean }`
  - `advancedFilters?: { fromAddress?: string; recipientAddress?: string; subject?: string; medicalDocumentType?: string; dateFrom?: string; dateTo?: string }`
- Si certaines propriétés manquent côté Angular alors qu'elles existent
  déjà dans le JSON backend, les ajouter au type TypeScript (équivalent à
  l'extension faite pour `MailThreadInfoDto` dans task-027 — c'est un
  alignement de surface, pas un changement de contrat).
- Si certaines propriétés ne sont **pas** dans le JSON backend, ouvrir
  `questions/task-029.md`.

### `features/mail/components/mail-search/`

- Refondre la structure du composant en un input + un dropdown (panel
  conditionnel) + un sous-panel « Recherche avancée ».
- Garder le selector `mss-mail-search` et les `@Output()` actuels
  (`searchResults`, `searchCleared`) pour ne pas casser `mail-list`.
- Signaux internes :
  - `query: WritableSignal<string>`
  - `isDropdownOpen: WritableSignal<boolean>`
  - `showAdvanced: WritableSignal<boolean>` (true → panel avancé visible)
  - `quickFilters: WritableSignal<{ isUnread: boolean; isImportant: boolean; hasAttachments: boolean }>`
  - `medicalFilter: WritableSignal<{ kind: 'all' | 'biology' | string | null }>`
    où `string` = un type médical (Consultation, Imagerie, …)
  - `dateFilter: WritableSignal<1 | 7 | 30 | 90 | null>`
  - `advancedForm: WritableSignal<{ fromAddress: string; recipientAddress: string; subject: string; medicalDocumentType: string }>`
  - `isSearching: WritableSignal<boolean>`
  - `hasResults: WritableSignal<boolean>` (déjà présent)
- Méthodes :
  - `toggleQuickFilter(key)`, `selectMedicalChip(type)`,
    `selectDateChip(days)`, `openAdvanced()`, `closeAdvanced()`,
    `applyAdvancedAndSearch()`, `clearAll()`, `executeSearch()`
- Computed :
  - `hasActiveFilters: Signal<boolean>` (true si n'importe quel chip ou
    champ avancé est non-vide)
  - `activeFilterCount: Signal<number>` (nombre de chips/champs actifs —
    affiché dans un petit badge à côté de l'input quand le dropdown est
    fermé pour signaler que des filtres sont appliqués)

### `features/mail/components/mail-list/`

- Aucun changement attendu côté logique. La chaîne signal task-027 doit
  rester compatible : la composante consomme toujours `displayedMails`,
  et la search ne fait que `state.emails.set(searchResults)` après quoi
  `displayedMails` recompose si Conversation est ON.

### Tests Vitest

≥ 6 tests dans `mail-search.component.spec.ts` (créer si absent) :

1. `renders the closed input by default` — au mount, le dropdown est fermé
   (vérifier l'absence du sélecteur `[data-testid="search-dropdown"]`).
2. `opens the dropdown on focus` — focus l'input, vérifier que le dropdown
   et tous ses sections (quick-filters, medical, dates, advanced toggle)
   sont rendus.
3. `applies an unread quick-filter and emits the search` — cliquer le chip
   « Non lus », mock l'API, vérifier que `searchResults` émet et que
   `statusFilters.isRead === false` est passé dans la requête.
4. `applies a medical type chip and emits the search` — cliquer
   « Consultation », vérifier le payload `advancedFilters.medicalDocumentType`.
5. `date chips are mutually exclusive` — cliquer 7j puis 30j, vérifier que
   seul 30j reste actif.
6. `clear button resets every filter and emits searchCleared` — activer
   plusieurs filtres, cliquer clear, vérifier que tous les signaux internes
   sont reset et `searchCleared` émis.
7. (Bonus) `advanced panel renders the 14 medical types in the select` —
   ouvrir le panel avancé, ouvrir le sélecteur, compter les options.

## Convention scellée

- **Single source of truth pour les filtres** : tous les états vivent dans
  les signaux du composant `mail-search`. La requête envoyée au backend
  est composée à l'envoi, pas stockée séparément.
- **Pas de chip multi-sélection ambigu** : sur les dimensions où Blazor
  rend les chips mutuellement exclusifs (dates, type médical), Angular
  fait pareil pour préserver la parité du modèle mental.
- **`searchMode` et `searchType` restent à 3** (sémantique combinée) —
  hors scope de la cette US, ces deux modes sont déjà choisis par défaut
  côté Blazor.

## Definition of Done

- [ ] `nx build mss-lib` passe (0 errors)
- [ ] `nx test mss-lib` passe (0 failures)
- [ ] Tous les fichiers Angular touchés : `mail-search.component.ts`,
  `mail-search.component.html`, `mail-search.component.scss`,
  `mail-search.component.spec.ts` (nouveau), `core/models/search.model.ts`
  (extension type uniquement, si nécessaire)
- [ ] **3 chips QuickFilters** rendus (data-testids :
  `mail-search-quick-unread`, `mail-search-quick-important`,
  `mail-search-quick-attachment`)
- [ ] **6 chips médicaux** rendus (data-testids :
  `mail-search-medical-all`, `-biology`, `-consultation`, `-imagerie`,
  `-prescription`, `-hospitalisation`)
- [ ] **4 chips de dates** rendus, mutuellement exclusifs (data-testids :
  `mail-search-date-1`, `-7`, `-30`, `-90`)
- [ ] **Panel Recherche avancée** : 3 inputs + 1 select des 14 types
  médicaux (data-testids : `mail-search-advanced-from`,
  `-recipient`, `-subject`, `-doc-type`)
- [ ] Bouton clear visible uniquement quand `query || filtersActive`
  (data-testid : `mail-search-clear`)
- [ ] Spinner pendant le chargement, input disabled
- [ ] Le dropdown se ferme au click extérieur ET sur Escape
- [ ] Compatibilité Mode Conversation (task-027) : les résultats respectent
  `displayedMails` quand Conversation ON
- [ ] **6+ tests Vitest verts** sur `mail-search.component.spec.ts`
- [ ] Aucune régression sur la suite mss-lib existante (105 tests verts en
  date de task-027 → ≥ 111 verts après cette US)
- [ ] **Aucun changement** sur `Api/Mail/`, `Dtos/`, `Client/Blazor/`,
  `devops`
- [ ] **Audit grep DOD** :
  - [ ] `grep -r "data-testid=\"mail-search-" Client/Angular/front/libs/mss/src/` → matches sur les ~14 testids ci-dessus
  - [ ] `grep -r "statusFilters\|contentFilters\|advancedFilters" Client/Angular/front/libs/mss/src/features/mail/` → matches dans le composant et son spec
  - [ ] `grep -rn "searchType: 3" Client/Angular/front/libs/mss/src/features/mail/components/mail-search/` → exactement 1 occurrence (dans le composant — la valeur reste hard-codée à 3 par scope)

## Manual Test Plan

### Setup

1. `cd Api/Mail/src/AppHost && dotnet run --launch-profile https`
2. `cd Client/Angular/front && npm start`
3. Loguer en doctor avec une boîte qui contient au minimum :
   - 5+ mails non lus
   - 2+ mails marqués importants
   - 3+ mails avec PJ
   - 5+ mails contenant des documents médicaux (au moins 1 Consultation,
     1 Imagerie, 1 Prescription, 1 Hospitalisation, 1 Biologie)

### Vérification 1 — input + dropdown

1. Aller sur Inbox.
2. Cliquer dans l'input de recherche.
3. **Vérifier** : le dropdown s'ouvre, montre les 3 sections (QuickFilters,
   Contenu médical, Dates), un bouton « Recherche avancée », pas le panel
   avancé encore.

### Vérification 2 — quick-filter unread

1. Cliquer le chip « Non lus ».
2. **Vérifier** : la liste se filtre instantanément aux non-lus, le chip
   reste actif (style coloré), un badge « 1 filtre » apparaît à côté de
   l'input. Le dropdown reste ouvert.

### Vérification 3 — chip médical

1. Sans collapse, cliquer le chip « Consultation ».
2. **Vérifier** : la liste se réduit aux mails avec un document de type
   Consultation. Si « Non lus » reste actif, l'intersection est appliquée.

### Vérification 4 — chips dates mutuellement exclusifs

1. Cliquer « 7 derniers jours ».
2. Cliquer « 30 derniers jours ».
3. **Vérifier** : seul « 30 derniers jours » reste actif, « 7 jours » se
   désactive automatiquement. La liste se met à jour.

### Vérification 5 — panel avancé

1. Cliquer « Recherche avancée ».
2. **Vérifier** : le dropdown bascule sur un panel avec les champs De / À
   ou CC / Objet + un sélecteur « Type de document » qui liste les 14 types.
3. Saisir un email dans « De » et cliquer Enter (ou bouton « Rechercher »
   selon implé).
4. **Vérifier** : la liste se filtre par cet expéditeur.

### Vérification 6 — bouton clear

1. Avec plusieurs filtres actifs et du texte dans l'input, cliquer la
   croix « clear ».
2. **Vérifier** : input vidé, tous les chips désactivés, panel avancé
   reset, liste rebascule sur l'inbox standard.

### Vérification 7 — interaction avec le mode Conversation (task-027)

1. Settings MSS → activer « Mode conversation ».
2. Revenir Inbox, taper une recherche qui ramène un fil multi-messages.
3. **Vérifier** : les résultats sont eux aussi réduits aux feuilles, le
   chip « N messages » apparaît, le bouton chevron déplie le fil sur les
   résultats. Désactiver le mode → la liste de résultats repasse en plat.

### Vérification 8 — Escape

1. Avec le dropdown ouvert, presser `Escape`.
2. **Vérifier** : le dropdown se referme. Re-presser n'a pas d'effet.

## Limites

- **Pas d'historique de recherches** — out of scope, candidat task-030 ou
  follow-up dédié.
- **Pas de suggestions auto-complete** sur l'input — out of scope.
- **Pas de raccourci clavier global** (ex. Ctrl+K) — out of scope, candidat
  task-030.
- **`searchMode` / `searchType` restent à 3** — la pertinence des
  résultats fera l'objet d'une US dédiée distincte (à backloguer après
  task-030).

## References

- `Client/Blazor/Src/Modules/Mss/Plugin/Components/SearchMailComponent.razor`
  (référence d'implémentation — lecture seule, 848 lignes)
- `Api/Mail/src/Api/Controllers/V1/SearchController.cs`
  (endpoints `POST /api/v1/search/semantic` et `/patient` — déjà câblés)
- archived-task-016 — alignement fonctionnel précédent Blazor → Angular
  (8 écarts UX livrés), même esprit (parité iso-fonctionnalité frontends F004)
- done-task-027 — mode conversation Angular ; cette US doit rester compatible
  avec le filtrage feuilles de `displayedMails`

## Branches

- `client-angular` (code-only) : forge writes code on the branch currently checked out in `Client/Angular/` — humain gère branche, commit, push, PR TFS. Snapshot au /start : `feature/nova-rewriting-mss-fixes-20260410`.

## Develop log

- Repos touched : `client-angular` (code-only — single repo, single frontend).
- DTOs / interop publiés : aucun (US Angular pure, contrat backend déjà figé).
- Files modified (uncommitted, on `feature/nova-rewriting-mss-fixes-20260410`) :
  - `front/libs/mss/src/features/mail/components/mail-search/mail-search.component.ts` (refonte)
  - `front/libs/mss/src/features/mail/components/mail-search/mail-search.component.html` (refonte)
  - `front/libs/mss/src/features/mail/components/mail-search/mail-search.component.scss` (étendu)
  - `front/libs/mss/src/features/mail/components/mail-search/mail-search.component.spec.ts` (nouveau)
- Modèle `core/models/search.model.ts` : **aucun changement** — `SearchRequestDto.filters` (`SearchFilterDto`) expose déjà `fieldFilters`, `statusFilters`, `dateFilters`, `contentFilters`, `patientFilters` côté Angular. Le modèle TypeScript était déjà aligné sur le DTO C#.
- Build / test :
  - `nx build mss-lib` : ✓ vert (production config)
  - `nx test mss-lib` : ✓ 13 fichiers, **112 tests verts**, 0 failure (était 105 → +7 tests task-029)
- Decisions d'implémentation à signaler à `/review` :
  - **Mode List du dropdown reproduit fidèlement Blazor** : 3 sections (Statut, Médical, Période) + bouton Recherche avancée + panel avancé en sub-vue. Au passage retour panel→liste, `closeAdvanced()` reste l'unique bouton (pas de fermeture par Escape ciblée — Escape ferme tout le dropdown).
  - **Sync chip ↔ select avancé** : sélectionner un chip type médical (Consultation/Imagerie/Prescription/Hospitalisation) écrit aussi `advancedForm.medicalDocumentType` ; choisir un type dans le select avancé met à jour le chip si correspondance, ou laisse le chip inactif si type hors-chip (ex. Synthèse, Vaccination, …).
  - **`computeDateFrom`** utilise `new Date()` côté frontend pour calculer `sentDateFrom`. Backend reçoit l'ISO en UTC. Cohérent avec la pratique Blazor (`DateTime.Now.AddDays(-N)`).
  - **HostListener `document:click`** ferme le dropdown au clic extérieur. `ElementRef` injecté pour scoper. Performance OK pour un composant unique sur la page.
  - **Toast d'erreur recherche** : non implémenté côté task-029 (pas demandé par la DOD). Une erreur API `semanticSearch` reset juste `isSearching` ; aucune notification utilisateur. Suggestion follow-up si retour utilisateur le réclame.
- DOD self-check (réalisable par commande) :
  - [x] `nx build mss-lib` 0 erreur
  - [x] `nx test mss-lib` 0 failure (112 tests verts, +7 nouveaux)
  - [x] 3 chips QuickFilters rendus avec les data-testids requis
  - [x] 6 chips médicaux rendus (mail-search-medical-{all|biology|consultation|imagerie|prescription|hospitalisation})
  - [x] 4 chips dates rendus, mutuellement exclusifs (vérifié dans le test #5)
  - [x] Panel Recherche avancée : 3 inputs + 1 select listant les 14 types (vérifié dans le test #6 : 14 types + option « Aucun filtre » = 15 options)
  - [x] Bouton clear visible conditionnellement, reset complet (vérifié dans le test #7)
  - [x] Spinner pendant le chargement, input disabled (`[disabled]="isSearching()"`)
  - [x] Dropdown se ferme au click extérieur (HostListener `document:click`) ET sur Escape (HostListener `document:keydown`)
  - [x] Compatibilité Mode Conversation (task-027) maintenue par construction : la chaîne signaux (`state.emails.set` → `displayedMails`) fonctionne sur n'importe quel jeu de mails, y compris les résultats de recherche.
  - [x] Aucune régression sur la suite mss-lib (105 → 112, +7 nouveaux uniquement)
  - [x] Aucun changement sur `Api/Mail/`, `Dtos/`, `Client/Blazor/`, `devops`
  - [x] Audit grep DOD :
    - `data-testid="mail-search-` → **16 matches** dans `mail-search.component.html` (≥ 14 attendus)
    - `statusFilters|contentFilters|advancedFilters` → matches dans `mail-search.component.ts` + `.spec.ts` (composant + spec)
    - `searchType: 3` → **1 match** dans `mail-search.component.ts` (l'unique occurrence, dans `buildRequest`)
- Observable behaviour items (deferred to manual test — HAG, règle 10) :
  - Ouverture / fermeture fluide du dropdown au focus / clic / Escape / clic extérieur
  - Réactivité visuelle des chips actifs (couleur primaire / médical / date)
  - Spinner visible pendant le chargement
  - Liste de résultats correctement filtrée par chaque combinaison de critères
  - Bascule mode Conversation → résultats de recherche en feuilles de fil avec chip + chevron
- Code-only : **aucun commit, aucun push** — l'humain (Pascal) gère les opérations git Angular et la PR TFS. Note : la branche actuelle contient déjà les changements task-027 non encore mergés ; les changements task-029 s'empilent dessus, l'humain pourra soit les commit séparément soit en bloc selon sa stratégie TFS.
- Next step : `/review task-029` (pas d'`api-mail` touché → `/sonar` skippé per agents/develop.md).

## PRs

- `client-angular` (code-only — humain gère commit/push TFS et ouverture PR). Liste des fichiers modifiés sur la branche `feature/nova-rewriting-mss-fixes-20260410` (uncommitted, **inclut aussi le diff task-027 non encore commit**) :
  - **task-029 (cette US)** :
    - `front/libs/mss/src/features/mail/components/mail-search/mail-search.component.ts` (refonte)
    - `front/libs/mss/src/features/mail/components/mail-search/mail-search.component.html` (refonte)
    - `front/libs/mss/src/features/mail/components/mail-search/mail-search.component.scss` (étendu)
    - `front/libs/mss/src/features/mail/components/mail-search/mail-search.component.spec.ts` (nouveau)
  - **task-027 (déjà livrée, en attente de commit/push TFS par Pascal)** :
    - `mail-header.component.{html,scss,spec.ts,ts}`
    - `mail-list.component.{html,ts}`
    - `mail-state.service.ts` + `mail-state.service.spec.ts` (nouveau)
- Forge a re-validé build + test (mss-lib) avant la transition `done-*` :
  - `nx build mss-lib` ✓ (cache hit)
  - `nx test mss-lib` ✓ (cache hit) — 13 fichiers, **112 tests verts**

## Code Review Summary

Verdict : **APPROVED** — 4 fichiers revus (task-029 uniquement, task-027 déjà reviewée précédemment), 3 suggestions non bloquantes, 0 issue bloquante.

### Files reviewed (task-029)

- `mail-search.component.ts` — ✅ structure claire avec catalogues const (`MEDICAL_TYPE_CHIPS`, `DATE_CHIPS`, `ALL_MEDICAL_TYPES`), 3 signaux distincts pour les dimensions de filtrage, computed `activeFilterCount` qui agrège tout en un endroit. `executeSearch()` court-circuite proprement vers `searchCleared.emit()` quand les critères sont vides (évite les hits backend inutiles). `HostListener('document:click')` pour fermer au clic extérieur, `document:keydown` pour Escape — pattern Angular idiomatique. JSDoc sur les méthodes publiques clés. Single source of truth `medicalType` synchronisé bidirectionnellement entre chip et select avancé.
- `mail-search.component.html` — ✅ chips en boucle `@for` avec catalogues const, classes BEM (`mail-search-chip--active`, `--medical`, `--date`), `data-testid` posés sur tous les éléments interactifs (16 occurrences). `aria-label` sur les boutons d'action. `[disabled]="isSearching()"` sur l'input. Panel avancé proprement séparé avec bouton retour.
- `mail-search.component.scss` — ✅ palette différenciée Statut (primaire bleu) / Médical (violet) / Période (vert) → cohérent avec le code couleur Blazor. Animation `mail-search-dropdown-slide` 0.12s. Variables CSS `--ds-color-*` avec fallbacks défensifs. Z-index 50 sur le dropdown (au-dessus de la liste de mails).
- `mail-search.component.spec.ts` — ✅ 7 tests (≥ 6 requis), couvre lifecycle (closed/opened), 3 chips de statut + emit, chip type médical + payload, exclusivité dates, 14 types dans le select avancé, clear reset complet. Mocks `MssApiService` via `vi.fn()`, `MailStateService` réel pour vérifier la chaîne signaux. Setup propre avec `TestBed.resetTestingModule()`.

### Suggestions (non-blocking)

1. **`buildFilters` émet des sub-objects vides** quand aucun filtre n'est actif — `statusFilters: {}`, `contentFilters: {}`, `fieldFilters: {}`. Le backend tolère, mais une garde conditionnelle (n'émettre la clé que si non-vide) réduirait la taille du payload. Optimisation cosmétique, candidate follow-up.
2. **Pas de raccourci `Enter` dans les champs du panel avancé** — seul le bouton « Rechercher » déclenche la recherche depuis ces champs. Le main input réagit à Enter via `onKeyDown`. UX explicite, acceptable pour le scope parité, mais un `(keydown.enter)="applyAdvancedAndSearch()"` sur les 3 inputs avancés serait un quick-win UX.
3. **`HostListener('document:click')` global** — ajoute un listener au document. Sur une app à un seul `mail-search` c'est négligeable. Si le composant est utilisé dans plusieurs contextes parallèles à l'avenir, considérer un détacheur partagé.

### Blocking Issues

Aucun.

### Note sur le diff bundled task-027

Le working tree de `Client/Angular/` contient à la fois les changements task-029 (cette US) ET les changements task-027 (US précédente, **déjà livrée et reviewée**) qui n'ont pas encore été commit/push par l'humain sur TFS. Cette imbrication est attendue en mode code-only — l'humain est libre de commit task-027 et task-029 séparément (`git commit` ciblé par fichiers) ou en bloc selon sa stratégie de gestion TFS. La review forge ne se prononce pas sur le sequencing des commits, juste sur la qualité du code écrit pour task-029.

## Post-review fix — Race condition multi-filtres (2026-05-04)

**Bug rapporté par Pascal lors du test manuel** : en sélectionnant successivement 3 chips (Aujourd'hui + Pièces jointes + Biologie), la liste de résultats donnait l'impression d'un OR au lieu d'un AND — plus de résultats à 3 filtres qu'avec un seul, comportement contre-intuitif.

### Diagnostic

1. **Backend AND vérifié** — lecture de `SemanticSearchRepository.SearchByFiltersAsync` : chaque dimension de filtre est appliquée via `query.Where(...)` cumulatif sur la même `IQueryable<Mail>`. `query = query.Where(m => m.SentDate >= ...)`, `query = query.Where(m => m.MailAttachments.Any())`, `query = query.Where(m => m.HasBiologyResults)` — c'est strictement un AND. Le service `SemanticSearchService.SearchAsync` route vers ce repo et intersecte ensuite avec les résultats sémantiques. **Pas de bug backend**.
2. **Bug client : race condition** — le `fireSearch` original utilisait `this.api.semanticSearch(request).pipe(takeUntilDestroyed(this.destroyRef)).subscribe(...)`. Chaque clic de chip déclenche un nouvel appel HTTP **sans annuler les précédents**. Quand 3 chips sont cliqués rapidement, 3 requêtes partent en parallèle ; selon la latence réseau, la **première** requête (la plus permissive, donc la plus longue à retourner beaucoup de résultats) peut arriver **après** la troisième (plus restrictive, plus rapide). Le `subscribe` traite chaque réponse à la chaîne → l'`searchResults.emit()` final correspond à la requête arrivée en dernier, **pas à la dernière requête envoyée**. D'où l'impression d'OR. Le Blazor évite cela via `CancellationTokenSource` (cf. `SearchMailComponent.razor:302`) ; le clone Angular initial avait omis cette protection.

### Correctif

Refonte du pipeline en `Subject + switchMap` :

```typescript
private readonly searchTrigger$ = new Subject<SearchRequestDto>()

constructor() {
  this.searchTrigger$
    .pipe(
      switchMap((request) => this.api.semanticSearch(request).pipe(catchError(...))),
      takeUntilDestroyed(this.destroyRef)
    )
    .subscribe((response) => { /* emit only the LATEST response's UIDs */ })
}

private fireSearch(request: SearchRequestDto): void {
  this.isSearching.set(true)
  this.searchTrigger$.next(request)  // switchMap cancels in-flight previous
}
```

`switchMap` annule l'Observable interne (donc cancel l'HTTP request via Angular HttpClient) dès qu'une nouvelle émission arrive sur `searchTrigger$`. Comportement équivalent au `CancellationTokenSource` côté Blazor.

### Tests ajoutés

3 nouveaux tests dans `mail-search.component.spec.ts` (10 au total maintenant) :

1. **`three filters fired in sequence end up combined in the LATEST request payload`** — applique date + attachment + biology ; assert que le **dernier** appel `semanticSearch` porte les 3 filtres dans le même payload (`dateFilters.sentDateFrom` défini, `contentFilters.hasAttachments=true`, `contentFilters.hasBiologyResults=true`). C'est le test « validation des données reçues » réclamé par Pascal — il garantit que la composition AND est bien matérialisée côté client, indépendamment de la sémantique backend.
2. **`text query + 2 filter chips compose into a single payload`** — assert que `query` + `statusFilters.isRead` + `dateFilters.sentDateFrom` se retrouvent ensemble dans le dernier appel.
3. **`out-of-order responses : only the LATEST request's UIDs are emitted`** — utilise des `Subject<SearchResponseDto>` mockés pour simuler le pathologique : request1 démarre, request2 démarre, response1 arrive en premier (UIDs incorrects [100,200,300]), response2 arrive en second (UIDs corrects [42,43]). Le test vérifie que `searchResults.emit` n'est appelé qu'**une seule fois** et avec les UIDs de la **dernière** requête. C'est la garantie défensive contre la race condition — sans `switchMap`, ce test échouerait avec `[[100,200,300], [42,43]]` au lieu de `[[42,43]]`.

### Validation

- `nx build mss-lib` ✓
- `nx test mss-lib` ✓ — 13 fichiers, **115 tests verts** (112 → 115, +3 nouveaux). Aucune régression sur les 7 tests existants de `mail-search.component.spec.ts`, ni sur les 105 autres tests mss-lib.

### Fichiers modifiés (ce fix)

- `front/libs/mss/src/features/mail/components/mail-search/mail-search.component.ts` — pipeline refactored, imports rxjs (`Subject`, `switchMap`, `catchError`, `EMPTY`)
- `front/libs/mss/src/features/mail/components/mail-search/mail-search.component.spec.ts` — 3 nouveaux tests (combined-payload, query+filters, race-condition)

Mode code-only : reste uncommitted, l'humain commit/push à sa convenance. Le fix s'empile sur les changements task-027 + task-029 initiaux dans le working tree.

### Pourquoi ça n'a pas été détecté en review initiale

Le `/develop` initial avait écrit `takeUntilDestroyed` (idiomatique pour cleanup à la destruction) mais avait omis la protection contre les requêtes concurrentes — un cas limite qui n'apparaît pas en test unitaire trivial (single emission) mais devient évident avec une UX rapide-cliqueurs. La review aurait pu flagger cela comme suggestion non-bloquante mais ne l'avait pas fait. **Leçon pour les futurs composants à recherche** : tout endpoint déclenchable plus d'une fois par UX rapide doit être routé par `Subject + switchMap` ou équivalent (debounce, request token), pas par direct subscribe.

## Merged

- **Date** : 2026-05-04
- **Pushable PRs merged** : aucun (task-029 est code-only sur `client-angular` uniquement — aucune PR GitHub à merger côté forge)
- **`client-angular`** : managed manually by the human (commit / push / PR / merge TFS hors visibilité forge)
- **CI develop** : N/A (pas de merge GitHub côté repos forge-automated)
- **Validation humaine** : flag `--i-tested` présent — Pascal a validé la US end-to-end après le post-review fix race condition (`Subject + switchMap`). Le diff Angular livré combine task-029 (dropdown parité Blazor + élagage 14→6 chips) et son post-review fix (cancellation des requêtes concurrentes). Le framework de tests d'intégration backend (task-031, archivable séparément) confirme par construction que le backend faisait déjà du AND strict — donc cette attestation valide bien la correction UX côté Angular, pas une supposée fix backend.
