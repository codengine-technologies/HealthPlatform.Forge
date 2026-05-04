# todo-task-030.md — Refonte UX recherche en panneau latéral (Outlook-style)

**Repos**: client-blazor, client-angular
**Dependencies**: done-task-029
**Epic**: E009

## Objectif

Remplacer le **dropdown encombrant** au-dessus de l'inbox (Blazor) et son
clone Angular livré en task-029 par un **panneau latéral coulissant** style
Outlook, ouvrable à droite de la fenêtre principale. Tous les critères de
recherche (texte, quick-filters, contenu médical, plage de dates, recherche
avancée) sont déplacés dans ce panneau. La liste des mails se recompose en
**temps réel** au fur et à mesure que l'utilisateur applique des filtres.

**Frustration adressée** : le dropdown actuel alourdit visuellement la zone
de l'inbox, casse le rythme de lecture des mails, et superpose son contenu
à la liste pendant qu'on filtre. Le panneau latéral isole la mécanique de
filtrage hors de la zone de lecture.

**Périmètre UX uniquement.** La pertinence des résultats (ranking, scoring
sémantique, `searchMode`, `searchType`, `minSimilarity`) reste inchangée
— une US dédiée sera ouverte plus tard pour ce chantier.

> **Symétrie obligatoire** : le panneau est rigoureusement identique côté
> Blazor et Angular (mêmes critères, même mise en page, même comportement,
> même nomenclature). C'est la seule manière de garder les deux frontends
> alignés au lieu de re-créer un écart fonctionnel comme celui qui a motivé
> task-029.

## Contexte — d'où l'on part

### Avant (état après task-029)

Côté Blazor, dropdown sous l'input de recherche listant chips quick-filters,
chips médicaux, chips de dates, et un bouton « Recherche avancée » qui
bascule sur un sous-panel inline. Côté Angular, le même dropdown vient
d'être porté par task-029.

### Après (état cible task-030)

Le dropdown disparaît. À la place :

```
┌─────────────────────────────────────────────────────────────────────┐
│  Inbox             [🔍 input recherche]    [⚙ Filtres (×N)]   …    │
├─────────────────────────────────────────────────────────────────────┤
│ Folders │ Mail list                                │ Search panel   │
│         │  ────────────────                        │ (slide-in 200ms)│
│  Inbox  │  feuille fil 1                           │                │
│  Sent   │  feuille fil 2                           │  Statut         │
│  …      │  …                                       │   ☐ Non lus     │
│         │                                          │   ☐ Importants  │
│         │                                          │   ☐ PJ          │
│         │                                          │                 │
│         │                                          │  Médical        │
│         │                                          │   ☐ Tous        │
│         │                                          │   ☐ Biologie    │
│         │                                          │   ☐ Consultation│
│         │                                          │   ☐ Imagerie    │
│         │                                          │   ☐ Prescription│
│         │                                          │   ☐ Hospi       │
│         │                                          │                 │
│         │                                          │  Période        │
│         │                                          │   ○ Aujourd'hui │
│         │                                          │   ○ 7 j         │
│         │                                          │   ○ 30 j        │
│         │                                          │   ○ 3 mois      │
│         │                                          │                 │
│         │                                          │  Avancée        │
│         │                                          │    De           │
│         │                                          │    À / CC       │
│         │                                          │    Objet        │
│         │                                          │    Type doc ▼   │
│         │                                          │                 │
│         │                                          │  [Effacer]  [×] │
└─────────────────────────────────────────────────────────────────────┘
```

## Comportement attendu

### Ouverture / fermeture

- Le panneau s'ouvre au clic sur un nouveau **bouton « Filtres »** placé à
  droite de l'input de recherche, OU au focus dans l'input quand des
  filtres sont déjà actifs.
- Animation slide-in / slide-out 200ms (CSS `transform: translateX`).
- Largeur du panneau : **360 px** (desktop) — fixe, non redimensionnable.
- Fermeture explicite via :
  - bouton « ✕ » en haut à droite du panneau
  - touche `Escape` quand le panneau a le focus
  - clic à l'extérieur du panneau (sur la liste de mails ou ailleurs)
- L'input de recherche reste **toujours visible** dans la barre du haut,
  qu'il y ait des filtres actifs ou non, panneau ouvert ou fermé.

### Contenu du panneau

Tous les critères livrés en task-029 migrent vers le panneau, mais sous
forme de **cases à cocher / radios** plutôt que de chips colorés (parité
visuelle Outlook — la grille checkbox est plus dense et plus lisible que
les chips quand l'on en a une trentaine en vue) :

- **Statut** (cases à cocher cumulatives) : Non lus, Importants, Pièces jointes
- **Médical** (cases à cocher — les 6 mêmes choix que task-029, exclusion
  mutuelle préservée sur la dimension « type de document » via radio
  interne) : Tous les documents, Biologie, Consultation, Imagerie,
  Prescription, Hospitalisation
- **Période** (radio — exclusion mutuelle) : Aujourd'hui, 7 j, 30 j, 3 mois,
  + option « Personnalisée » qui révèle un date-picker (optionnel pour
  cette US — out of scope si non livrable, voir Limites)
- **Avancée** (4 champs) : De, À/CC, Objet, Type de document (sélecteur
  des 14 types, identique task-029)

### Filtrage en temps réel

- Toggle d'une case / radio → la liste se met à jour **immédiatement** (pas
  d'`Enter`, pas de bouton « Appliquer »). Idéalement < 200ms perçus.
- Saisie dans l'input texte ou dans les champs « De / À / Objet » →
  **debounce 250 ms** côté frontend avant d'envoyer la requête.
- Cas dégénéré : si l'utilisateur efface tout (texte + cases), la liste
  rebascule sur l'inbox standard (équivalent `loadEmails()`).

### Compteur de filtres actifs

- À côté du bouton « Filtres », badge numérique affichant le nombre de
  cases / radios / champs avancés non-vides actuellement appliqués.
- Le compteur reste visible quand le panneau est fermé pour rappeler à
  l'utilisateur qu'une recherche est en cours.
- Ex. : `Filtres ②` quand l'utilisateur a coché « Non lus » + « Imagerie ».

### Bouton « Effacer »

- Pied de panneau, libellé « Effacer les filtres ».
- Reset complet : décocher toutes les cases, vider les champs avancés,
  vider l'input texte, fermer le panneau (au choix : pas obligatoire de
  fermer — à valider PO ; ma préférence : NE PAS fermer, l'utilisateur
  vient peut-être de vouloir tout reset pour repartir d'une feuille
  blanche dans le même panneau).

### Compatibilité Mode Conversation (task-027)

- Le mode `MailViewMode.Conversation` reste un mode d'affichage : si actif,
  les **résultats de recherche** sont eux aussi réduits aux feuilles de
  fil. Le panneau ne touche pas à `mailViewMode`.

### Suppression de l'ancien dropdown

- Côté Blazor : démantèlement complet du bloc dropdown dans
  `SearchMailComponent.razor` ; il devient un simple input + un bouton
  « Filtres » qui pilote le panneau latéral.
- Côté Angular : démantèlement complet du dropdown livré en task-029 ;
  seule l'input + le bouton « Filtres » subsistent dans
  `mail-search.component.html`. Le panneau latéral est un nouveau composant.

## Périmètre détaillé

### `client-blazor` (pushed)

- **Nouveau composant** `SearchPanelComponent.razor` placé dans
  `Client/Blazor/Src/Modules/Mss/Plugin/Components/`.
- **Refonte** de `SearchMailComponent.razor` : la partie dropdown disparaît,
  le composant devient un input + un bouton « Filtres » + un placeholder
  pour l'animation. Le `SearchPanelComponent` se positionne via CSS
  absolute / fixed à droite.
- **Mise en page parente** (probablement `MailListComponent.razor` ou la
  page hôte) : prévoir un slot d'ancrage à droite de la zone mail-list pour
  que le panneau coulisse à un endroit cohérent du layout.
- Localizer : nouvelles clés FR + EN pour les libellés du panneau
  (« Filtres », « Statut », « Médical », « Période », « Avancée »,
  « Effacer les filtres »).

### `client-angular` (code-only)

- **Nouveau composant** `SearchPanelComponent` (standalone, OnPush) placé
  dans `Client/Angular/front/libs/mss/src/features/mail/components/search-panel/`.
- **Refonte** de `mail-search.component.html` / `.ts` : disparition du
  dropdown, ajout du bouton « Filtres » qui toggle un signal
  `state.isSearchPanelOpen`.
- **Mise en page** : insérer le `<mss-search-panel>` à droite dans le
  template parent (`mss-mail.component.html` ou `mail-list.component.html`
  selon le squelette actuel).
- État partagé : ajouter sur `mail-state.service.ts` un signal
  `isSearchPanelOpen: WritableSignal<boolean>` + un computed
  `activeFilterCount: Signal<number>` calculé depuis les signaux de filtres
  qui vivent dans le panel (ou dans le state — choix d'implé).
- Mode code-only : le forge écrit le code, **ne commit / push pas**, humain
  gère TFS.

### Tests

#### Blazor (bUnit)

≥ 4 tests sur `SearchPanelComponentTests.cs` :

1. `panel is hidden by default`
2. `panel slides in when toggle button is clicked`
3. `clicking outside closes the panel`
4. `applying a filter updates the active filter count badge`

#### Angular (Vitest)

≥ 4 tests dans `search-panel.component.spec.ts` (nouveau) :

1. `panel renders all 4 sections (statut / médical / période / avancée)`
2. `toggling a status checkbox emits a search request`
3. `clear button resets every filter and closes the panel`
4. `escape key closes the panel`

≥ 1 test dans `mail-search.component.spec.ts` (mise à jour de l'existant
post-029) :

5. `clicking the filters button toggles the search panel signal`

## Convention scellée

- **Une seule UX, deux frontends.** Tout pixel / case / libellé doit être
  identique entre Blazor et Angular. Toute divergence non justifiée est
  une régression.
- **Pas de double mécanique** : à la fin de la US, plus aucun dropdown de
  filtre dans la zone inbox côté Blazor ou Angular.
- **Filtres dans le panneau, pas dans le composant input** : le composant
  `mail-search` ne porte plus que l'input texte + le bouton ouvrir-panneau
  + le badge compteur. Toute la logique de filtrage migre dans
  `SearchPanelComponent`.
- **Périmètre UX strict** : pas de touche à `searchMode` / `searchType` /
  `minSimilarity` / scoring backend. Une US séparée traitera la pertinence.

## Definition of Done

- [ ] **Blazor** : `dotnet build HealthPlatform.Client.sln` 0 errors
- [ ] **Blazor** : `dotnet test HealthPlatform.Client.sln` 0 failures
- [ ] **Angular** : `nx build mss-lib` 0 errors
- [ ] **Angular** : `nx test mss-lib` 0 failures
- [ ] Bouton « Filtres » présent à droite de l'input de recherche, sur les
  deux frontends (data-testids : `mail-search-panel-toggle`)
- [ ] Panneau latéral 360 px à droite, slide-in / slide-out animé ~200 ms
  (data-testid : `mail-search-panel`)
- [ ] **Statut** : 3 cases à cocher (`mail-search-panel-status-unread`,
  `-important`, `-attachment`)
- [ ] **Médical** : 6 cases à cocher / radios selon l'exclusion logique
  (`mail-search-panel-medical-{all|biology|consultation|imagerie|prescription|hospitalisation}`)
- [ ] **Période** : 4 radios mutuellement exclusifs
  (`mail-search-panel-date-{today|7d|30d|90d}`)
- [ ] **Avancée** : 4 champs (`mail-search-panel-advanced-{from|recipient|subject|doc-type}`)
- [ ] Bouton « Effacer » au pied du panneau
  (`mail-search-panel-clear`)
- [ ] Bouton « ✕ » fermeture du panneau
  (`mail-search-panel-close`)
- [ ] Badge compteur `N filtres` visible uniquement quand au moins un
  filtre est actif
  (`mail-search-active-filter-count`)
- [ ] Filtrage en **temps réel** au toggle de case / radio (pas d'`Enter`
  nécessaire)
- [ ] Debounce **250 ms** sur l'input texte et les champs De / À / Objet
- [ ] Le panneau se ferme via : bouton ✕, Escape, clic extérieur
- [ ] Suppression complète de l'ancien dropdown sur Blazor (lignes de
  `SearchMailComponent.razor` correspondantes retirées)
- [ ] Suppression complète du dropdown Angular livré en task-029 dans
  `mail-search.component.html` / `.ts`
- [ ] Compatibilité Mode Conversation (task-027) maintenue : les résultats
  respectent `displayedMails` quand Conversation ON
- [ ] **Iso-pixel parité Blazor ↔ Angular** vérifiée manuellement sur les
  Vérifications 1 → 7 du Manual Test Plan (humain compare les deux)
- [ ] **Tests Blazor** : 4+ bUnit verts sur `SearchPanelComponentTests.cs`
- [ ] **Tests Angular** : 4+ Vitest verts sur `search-panel.component.spec.ts`
  + 1 test mis à jour sur `mail-search.component.spec.ts`
- [ ] **Audit grep DOD** :
  - [ ] `grep -rn "search-dropdown\|advanced-search-panel" Client/Blazor/Src/Modules/Mss/` → vide (l'ancien dropdown a disparu)
  - [ ] `grep -rn "search-dropdown" Client/Angular/front/libs/mss/src/` → vide
  - [ ] `grep -rn "data-testid=\"mail-search-panel-" Client/Blazor/Src/` Client/Angular/front/libs/mss/src/` → matches sur les ~13 testids ci-dessus, **côté Blazor ET côté Angular**
- [ ] **Aucun changement** sur `Api/Mail/`, `Dtos/`, `devops`,
  `Sdk/`, `Host/`, `interop/`, `psc-proxy-*`

## Manual Test Plan

### Setup

1. `cd Api/Mail/src/AppHost && dotnet run --launch-profile https`
2. `cd Client/Blazor && dotnet run` (frontend Blazor)
3. `cd Client/Angular/front && npm start` (frontend Angular)
4. Loguer en doctor avec une boîte qui contient le même mix qu'en task-029
   (5+ non lus, 2+ importants, 3+ avec PJ, 5+ avec docs médicaux mixés).

### Vérification 1 — bouton Filtres + ouverture du panneau

1. Sur l'Inbox de **chaque frontend** (Blazor d'abord, puis Angular),
   localiser le bouton « Filtres » à droite de l'input de recherche.
2. Cliquer le bouton.
3. **Vérifier** : le panneau coulisse depuis la droite, animation ~200ms,
   largeur 360px, contenu identique pixel-pour-pixel entre Blazor et
   Angular (faire les deux côte à côte sur deux fenêtres).

### Vérification 2 — toggle d'un filtre statut

1. Cocher « Non lus » dans le panneau.
2. **Vérifier** : la liste de mails se filtre **instantanément** (< 1
   seconde perçue) sans cliquer Enter, le badge compteur affiche « 1 ».

### Vérification 3 — toggle d'un filtre médical

1. Sans décocher « Non lus », cocher « Imagerie ».
2. **Vérifier** : la liste se réduit à l'intersection des deux. Badge « 2 ».

### Vérification 4 — radio période exclusive

1. Cliquer « 7 j ».
2. Cliquer « 30 j ».
3. **Vérifier** : seul « 30 j » reste sélectionné. Liste recomposée.

### Vérification 5 — recherche avancée

1. Saisir un email d'expéditeur dans le champ « De » du panneau.
2. **Vérifier** : après ~250 ms (debounce), la liste se filtre. Badge
   passe à « 3 ».

### Vérification 6 — fermeture par Escape / clic extérieur

1. Avec le panneau ouvert, presser `Escape`.
2. **Vérifier** : le panneau se referme, les filtres restent appliqués
   (la liste reste filtrée), badge « 3 » toujours visible à côté du bouton.
3. Re-cliquer sur l'icône Filtres pour ré-ouvrir → tous les filtres sont
   restaurés visuellement.
4. Clic en dehors du panneau (sur un mail).
5. **Vérifier** : le panneau se referme, l'état est conservé.

### Vérification 7 — bouton Effacer

1. Cliquer « Effacer les filtres » au pied du panneau.
2. **Vérifier** : toutes les cases sont décochées, tous les champs vidés,
   badge disparaît, la liste rebascule sur l'inbox standard, le panneau
   reste ouvert (état de remise à zéro pour repartir).

### Vérification 8 — interaction avec le mode Conversation (task-027)

1. Settings MSS → activer « Mode conversation ».
2. Inbox, ouvrir Filtres, cocher « Imagerie » + saisir « radio » dans
   l'input.
3. **Vérifier** : la liste de résultats applique le filtrage feuilles, le
   chip « N messages » apparaît sur les fils multi-messages, le bouton
   chevron déplie correctement les enfants.
4. Désactiver Conversation → la liste de résultats repasse en plat.

### Vérification 9 — iso parité Blazor ↔ Angular (manuelle)

1. Mettre Blazor et Angular côte à côte (deux navigateurs ou deux onglets
   sur écrans séparés).
2. Reproduire les vérifications 1 → 7 simultanément sur les deux.
3. **Vérifier** : les comportements sont strictement identiques (même
   timing d'animation, même typo, même écart inter-éléments, mêmes
   libellés FR — note : un humain bilingue peut comparer EN aussi en
   activant l'autre langue dans Settings).
4. Déclarer un mismatch s'il y en a un — bloquant pour le merge.

### Vérification 10 — anti-régression task-029 / inbox standard

1. Avec aucun filtre actif et le panneau fermé, vérifier que l'Inbox
   standard fonctionne normalement (pagination, sélection, mark-read,
   move, etc.).
2. Cliquer sur un mail → le détail s'ouvre normalement.

## Limites

- **Pas de mode mobile** dans le périmètre — on suppose desktop
  responsive ≥ 1280 px. Sur mobile / tablette < 1024 px, fallback : le
  panneau s'affiche en modale plein écran (à acter en implé si trivial,
  sinon out of scope, candidat follow-up).
- **Date « Personnalisée »** (date-picker) : nice-to-have, candidat
  out-of-scope si l'implé du panel + reste prend déjà tout le budget.
- **Historique de recherches** : out of scope, follow-up dédié.
- **Raccourci clavier global** (Ctrl+K pour ouvrir le panneau) : out of
  scope, follow-up dédié.
- **Pertinence des résultats** (scoring sémantique, ranking, modes
  combinés) : **out of scope strict**, US dédiée ouverte ultérieurement.
- **Auto-complete sur l'input texte** : out of scope.

## References

- `Client/Blazor/Src/Modules/Mss/Plugin/Components/SearchMailComponent.razor`
  (avant cette US — sera démantelé)
- done-task-029 — porte la couverture fonctionnelle de la recherche Angular
  à parité avec Blazor (préalable obligatoire à task-030)
- done-task-027 — mode conversation Angular, doit rester compatible
- archived-task-016 — alignement précédent Blazor → Angular (lignée F004
  iso-fonctionnalité frontends)
- Inspiration UX : Microsoft Outlook desktop (panneau latéral droit
  « Filtres » sur la vue Inbox)
