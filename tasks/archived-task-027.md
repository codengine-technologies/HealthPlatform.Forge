# todo-task-027.md — Vue conversation Angular (parité Blazor)

**Repos**: client-angular
**Single frontend**: true
**Dependencies**: —
**Epic**: E009

## Objectif

Apporter à Angular la **vue conversation** déjà opérationnelle en Blazor :
quand le médecin active le réglage « Mode conversation » dans ses
paramètres MSS, la liste des mails se replie sur les **feuilles de fil**
(les messages sans réponse ultérieure) et chaque ligne agrégeante affiche
un compteur du nombre de messages du fil + un bouton pour déplier ses
enfants en place.

Aujourd'hui le toggle existe déjà dans les settings Angular et le
backend (`GET /api/v1/mail/thread/{messageId}` + DTOs `MailThreadInfoDto`
/ `MailThreadItemDto` + service Angular `MssApiService.getThread`) est
prêt — mais le composant `mail-list` ignore complètement le réglage et
rend toujours une liste plate. La US est purement une finition Angular ;
zéro changement backend, DTO ou contrat.

## Contexte — où en sont les pièces

| Pièce | Côté Angular |
|---|---|
| Setting `MailViewMode` (enum List=0 / Conversation=1) | ✅ déjà dans `core/models/user-settings.model.ts` |
| Toggle « Mode conversation » dans la page Settings MSS | ✅ déjà dans `mss-settings.component.html/ts` |
| DTOs `MailThreadInfoDto` + `MailThreadItemDto` | ✅ déjà dans `core/models/mail.model.ts` |
| `MssApiService.getThread(messageId)` | ✅ déjà câblé |
| Filtrage `mail-list` selon le réglage | ❌ manquant |
| Affichage compteur + bouton expand sur `mail-header` | ❌ manquant |
| État « fil déplié » dans `mail-state.service` | ❌ manquant |
| Rendu indenté des enfants de fil | ❌ manquant |

Référence Blazor (lecture seule, pour parité) :
- `Client/Blazor/Src/Modules/Mss/Plugin/Components/MailListComponent.razor`
  - `GetDisplayedEmails()` (≈ ligne 384) : filtre les enfants de fil quand
    `MailViewMode == Conversation`
  - `CalculateThreadCounts()` (≈ ligne 419) : agrège le nombre de
    messages par root
  - `OnExpandThread()` (≈ ligne 1935) : charge le fil via le service
    et rend les enfants `IsThreadChild="true"` indentés
- `Client/Blazor/Src/Modules/Mss/Plugin/Components/SettingsComponent.razor`
  (lignes 265-274) : toggle de référence

## Comportement attendu

### Filtrage de la liste

- **Mode `List` (défaut)** : aucun changement par rapport à aujourd'hui
  — toutes les lignes sont rendues à plat.
- **Mode `Conversation`** :
  - Seules les **feuilles de fil** sont visibles dans la liste principale
    (un mail est une feuille s'il n'a pas de réponse ultérieure dans le
    dataset chargé du dossier courant).
  - Les fils mono-message (un seul mail, ni reply ni replied-to) restent
    visibles tels quels, sans badge ni bouton expand (un mail seul n'est
    pas une « conversation »).
  - L'ordre de la liste reste celui de la feuille (date du dernier
    message du fil), inchangé par rapport au mode List.

### Compteur + bouton expand sur l'en-tête de ligne

- Sur chaque ligne **feuille de fil multi-messages**, le composant
  `mail-header` affiche un petit chip à droite du sujet portant le
  nombre total de messages du fil (ex. « 4 messages »).
- Un bouton chevron (ou équivalent design system) permet de déplier le
  fil. Au clic :
  - Le client appelle `MssApiService.getThread(messageId)` et stocke
    le `MailThreadInfoDto` retourné dans le state.
  - Pendant le chargement, le chevron est remplacé par un spinner
    discret **sur le bouton lui-même** (pas un overlay sur la ligne).
  - Une fois le fil chargé, les enfants apparaissent **immédiatement
    sous la ligne root**, **indentés** visuellement (padding gauche
    accru — typiquement ~24-32px), avec un style « ligne enfant »
    (fond légèrement différent ou bordure gauche colorée).
  - Le bouton chevron pivote pour signifier l'état déplié.
- Au clic re-clic (ou click ailleurs sur une autre ligne) : le fil
  collapse, l'état est effacé du state, les enfants disparaissent.
- **Un seul fil déplié à la fois** (parité Blazor). Ouvrir un autre
  fil collapse automatiquement le précédent.
- Cliquer sur une ligne enfant ouvre le mail comme n'importe quel
  autre clic mail (handler de sélection identique aux feuilles).

### Réactivité du toggle settings

- Quand le médecin bascule le toggle « Mode conversation » dans la page
  Settings, la `mail-list` répond immédiatement (via les signals — pas
  de reload manuel). Le passage `Conversation → List` collapse tout fil
  ouvert et restaure la vue plate.

### Pas-de-fil (corner cases)

- Si l'API `getThread()` renvoie une erreur ou un fil vide
  (`threadCount == 0` ou `threadItems` vide), le client logge l'erreur,
  collapse le bouton (état non-déplié), affiche un toast d'erreur
  utilisateur générique, et ne crashe pas le rendu de la liste.
- Si un mail change de dossier pendant qu'on est déplié (cas rare) et
  que les enfants du fil ne sont plus dans le dataset chargé : ne pas
  les afficher en double, l'API `getThread` reste source de vérité.

## Périmètre détaillé

### `core/models/`
- **Aucune modification.** Les DTOs `MailThreadInfoDto` /
  `MailThreadItemDto` et l'enum `MailViewMode` sont déjà publiés.

### `features/mail/services/mail-state.service.ts`
- Exposer un computed signal `mailViewMode` qui lit le réglage utilisateur
  (déjà présent dans le store settings ; à câbler en lecture seule).
- Ajouter un signal `expandedThreadMessageId: WritableSignal<string | null>`.
- Ajouter un signal `expandedThreadInfo: WritableSignal<MailThreadInfoDto | null>`.
- Ajouter un signal `isLoadingThread: WritableSignal<boolean>`.
- Ajouter une méthode `expandThread(messageId: string): void` qui :
  - Si un autre fil est déjà déplié → le collapse en premier.
  - Bascule `isLoadingThread = true`, appelle `getThread(messageId)`,
    écrit `expandedThreadInfo` au succès, écrit `expandedThreadMessageId`,
    bascule `isLoadingThread = false`. Sur erreur : toast + reset clean.
- Ajouter une méthode `collapseThread(): void` qui clear les 3 signals.
- Exposer un computed `displayedMails` qui retourne :
  - En mode `List` → tous les mails du dossier courant
  - En mode `Conversation` → uniquement les feuilles (mails dont aucun
    autre mail du dataset ne porte leur `messageId` en `replyTo` /
    `references`)
- Exposer un computed `threadCounts: Map<messageId, number>` qui agrège
  le nombre de messages par root. Utilisé par `mail-header` pour le chip.

> **Note d'implémentation — pas une décision business** : le calcul des
> feuilles et des compteurs côté client se base sur le dataset chargé
> du dossier (parité Blazor `CalculateThreadCounts`). La logique précise
> du regroupement (par `subject` normalisé / `references` / `inReplyTo`)
> est laissée au choix du dev — l'objectif business est : « un mail qui
> a une réponse plus récente disparaît de la liste principale ; le
> compteur sur le root est correct ». Si une ambiguïté apparaît à
> l'implé, ouvrir une `questions/task-027.md`.

### `features/mail/components/mail-list/`
- Utiliser le computed `displayedMails` du service au lieu de
  l'observable plat actuel.
- Quand un fil est déplié, intercaler les `threadItems` correspondants
  juste après le mail root, avec une prop `isThreadChild: true` passée à
  `mail-header` (ou via une variable de template).

### `features/mail/components/mail-header/`
- Nouveau input `threadCount?: number` — quand `> 1` ET `isThreadChild != true`,
  afficher le chip « N messages ».
- Nouveau input `isExpanded?: boolean` — pilote l'icône chevron.
- Nouveau input `isLoadingThread?: boolean` — bascule le chevron en spinner.
- Nouvel output `(toggleThread)` émis au click du chevron.
- Nouveau input `isThreadChild?: boolean` (default false) — applique la
  classe CSS `mail-header--thread-child` (padding-left accru, fond
  altéré ou bordure gauche colorée). Le chip et le bouton expand sont
  cachés sur les enfants.

### Settings UI Angular
- **Aucune modification.** Le toggle existe déjà.

### Tests Vitest

≥ 4 tests dans `mail-state.service.spec.ts` (créer si absent) :

1. `displayedMails returns flat list when mailViewMode == List` —
   data : 3 mails, dont 2 dans le même fil. Attendu : 3 lignes.
2. `displayedMails returns leaves only when mailViewMode == Conversation` —
   même data. Attendu : 2 lignes (la feuille du fil + le solo).
3. `expandThread loads thread info and sets state` —
   mock `MssApiService.getThread` retourne un `MailThreadInfoDto` ;
   après `expandThread('msg-1')`, attendu : `expandedThreadMessageId === 'msg-1'`,
   `expandedThreadInfo` = mock, `isLoadingThread === false`.
4. `collapseThread clears state` — après expand puis collapse, les 3
   signals reviennent à leur valeur initiale.

≥ 1 test bonus dans `mail-header.component.spec.ts` (ou nouveau spec) :

5. `mail-header renders thread count chip when threadCount > 1` —
   render `<mail-header [threadCount]="4" [isThreadChild]="false" />`,
   attendu : chip texte « 4 messages » présent + bouton chevron présent.
   Avec `[isThreadChild]="true"`, attendu : ni chip ni chevron.

## Convention scellée

- **Single source of truth pour le mode** : la valeur du réglage est lue
  via le computed signal du service ; aucun composant ne lit
  directement le store settings.
- **Single source of truth pour les compteurs** : `threadCounts` est un
  computed du service, pas un calcul fait dans le template.
- **Un seul fil déplié à la fois** : ouvrir un fil collapse l'autre.
- **Mode `Conversation` ne masque jamais un mail solo** : un mail sans
  reply ni replied-to reste visible avec son rendu standard, sans chip.
- **Reset à `Conversation → List`** : tout fil ouvert collapse
  automatiquement.

## Definition of Done

- [ ] `npm run build` passe (0 errors) sur `Client/Angular/front/`
- [ ] `npm test` passe (0 failures) sur `Client/Angular/front/`
- [ ] **Service** : computed `displayedMails`, computed `threadCounts`,
  signals `expandedThreadMessageId` / `expandedThreadInfo` / `isLoadingThread`,
  méthodes `expandThread()` / `collapseThread()` implémentés
- [ ] **Service** : 4+ tests Vitest verts (filtrage List vs Conversation,
  expandThread succès, collapseThread clear, gestion erreur API)
- [ ] **`mail-list`** : utilise `displayedMails` à la place de la liste plate ;
  intercale les enfants de fil après le root quand le fil est déplié,
  rendu indenté
- [ ] **`mail-header`** : nouveaux inputs `threadCount` / `isExpanded` /
  `isLoadingThread` / `isThreadChild` + output `(toggleThread)` ;
  chip et bouton uniquement quand `threadCount > 1 && !isThreadChild`
- [ ] **`mail-header`** : 1+ test Vitest sur le rendu du chip et du bouton
- [ ] **`data-testid`** posés : `mail-list-row-thread-toggle`,
  `mail-list-row-thread-count`, `mail-list-row-thread-child`
- [ ] **Réactivité** : basculer le toggle settings live recompose la
  liste sans rechargement manuel ; tout fil ouvert collapse au passage
  `Conversation → List`
- [ ] **Aucune régression** : suite Vitest mss-lib reste verte (incl. les
  tests `mail-list` existants en mode List, qui doivent rester GREEN)
- [ ] **Audit grep DOD** :
  - [ ] `grep -r "mailViewMode" Client/Angular/front/libs/mss/src/features/mail/` →
    matches dans le service + composant `mail-list`
  - [ ] `grep -r "expandedThreadMessageId" Client/Angular/front/libs/mss/src/` →
    matches uniquement dans `mail-state.service.ts` et son spec
  - [ ] `grep -r "isThreadChild" Client/Angular/front/libs/mss/src/` →
    matches dans `mail-header` (template + .ts) et `mail-list` (template)
- [ ] **Aucun changement** sur `Api/Mail/`, `Dtos/`, `Client/Blazor/`, devops

## Manual Test Plan

### Setup
1. `cd Api/Mail/src/AppHost && dotnet run --launch-profile https`
2. `cd Client/Angular/front && npm start`
3. Loguer en tant que doctor avec une boîte qui contient au moins
   un fil multi-messages (utiliser un compte test avec un thread
   « Re: Re: Re: ... » d'au moins 3 messages).

### Vérification 1 — comportement par défaut (mode List)
1. Ouvrir Settings MSS, vérifier que « Mode conversation » est **OFF**.
2. Aller sur Inbox.
3. **Vérifier** : tous les messages sont listés à plat, aucun chip
   « N messages » nulle part, aucun bouton expand.

### Vérification 2 — bascule en mode Conversation
1. Settings MSS → activer « Mode conversation ».
2. Revenir sur Inbox.
3. **Vérifier** : la liste s'est recomposée, seules les feuilles des
   fils multi-messages restent visibles, les mails solo restent visibles
   sans badge.
4. **Vérifier** : sur la (les) feuille(s) de fil multi-messages, un chip
   « N messages » s'affiche à droite du sujet, et un bouton chevron à
   côté.

### Vérification 3 — déploiement d'un fil
1. Cliquer sur le bouton chevron d'un fil de 3+ messages.
2. **Vérifier** : pendant ~quelques centaines de ms, le chevron est
   remplacé par un petit spinner.
3. **Vérifier** : les messages enfants apparaissent juste sous la ligne
   root, indentés visuellement (padding gauche), dans l'ordre
   chronologique inverse (plus récent en haut, parité avec Blazor).
4. **Vérifier** : le chevron a pivoté pour signifier l'état déplié.

### Vérification 4 — déploiement d'un autre fil
1. Sans collapse le premier, cliquer sur le chevron d'un autre fil.
2. **Vérifier** : le premier fil collapse automatiquement, le second
   se déplie. Un seul fil déplié à la fois.

### Vérification 5 — collapse manuel
1. Re-cliquer sur le chevron du fil déplié.
2. **Vérifier** : les enfants disparaissent, le chevron pivote en
   position fermée.

### Vérification 6 — clic sur un enfant
1. Déplier un fil, cliquer sur un message enfant.
2. **Vérifier** : le détail du mail enfant s'ouvre normalement (parité
   avec un clic sur n'importe quel autre mail).

### Vérification 7 — bascule retour au mode List
1. Avec un fil déplié, retourner dans Settings MSS et désactiver
   « Mode conversation ».
2. Revenir sur Inbox.
3. **Vérifier** : la liste est repassée en mode plat, le fil n'est
   plus déplié, tous les mails sont à nouveau visibles.

### Vérification 8 — erreur API (optionnel — si reproductible)
1. Bloquer ou couper le réseau.
2. Cliquer sur un bouton chevron.
3. **Vérifier** : un toast d'erreur apparaît, le bouton revient en
   position fermée, l'app ne crashe pas.

## Limites

- **Pas de cross-folder threading** : si une réponse à un mail Inbox
  vit dans Sent, elle ne sera pas remontée comme enfant du fil dans
  Inbox — la US se limite au regroupement intra-dossier (parité Blazor
  actuelle, le backend `getThread` retourne le fil cross-folder mais
  le filtrage côté client se limite au dataset chargé).
- **Pas de raccourci clavier** pour expand/collapse — out of scope,
  follow-up si demandé par retour utilisateur.
- **Pas d'indicateur « fil contient un non-lu »** sur la ligne root —
  out of scope, follow-up si demandé.

## References

- `Client/Blazor/Src/Modules/Mss/Plugin/Components/MailListComponent.razor`
  (référence d'implémentation — lecture seule)
- `Client/Blazor/Src/Modules/Mss/Plugin/Components/SettingsComponent.razor`
  lignes 265-274 (toggle de référence — déjà porté côté Angular)
- `Api/Mail/src/Api/Controllers/V1/MailController.cs` lignes 1466-1497
  (endpoint backend `GetThreadAsync` — déjà câblé côté Angular service)
- archived-task-016 — alignement fonctionnel précédent Blazor → Angular,
  même esprit (parité UX / iso-fonctionnalité frontends F004)

## Branches

- `client-angular` (code-only) : forge writes code on the branch currently checked out in `Client/Angular/` — humain gère branche, commit, push, PR TFS. Snapshot au /start : `feature/nova-rewriting-mss-fixes-20260410`.

## Develop log

- Repos touched : `client-angular` (code-only — aucune autre repo dans `**Repos**:`).
- DTOs published : aucun (US purement frontend Angular, contrat backend déjà figé).
- Interop published : aucun.
- Files modified (uncommitted, on `feature/nova-rewriting-mss-fixes-20260410`) :
  - `front/libs/mss/src/features/mail/services/mail-state.service.ts`
  - `front/libs/mss/src/features/mail/services/mail-state.service.spec.ts` (nouveau)
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.html`
  - `front/libs/mss/src/features/mail/components/mail-header/mail-header.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-header/mail-header.component.html`
  - `front/libs/mss/src/features/mail/components/mail-header/mail-header.component.scss`
  - `front/libs/mss/src/features/mail/components/mail-header/mail-header.component.spec.ts`
- Build / test :
  - `nx build mss-lib` : ✓ vert (production config)
  - `nx test mss-lib` : ✓ 12 fichiers, **105 tests verts**, 0 failure
  - `nx build weda2` : ⚠ pré-existant — bundle initial dépasse le budget (1.65 MB vs 1.50 MB) et `daily-agenda.page.scss` dépasse le budget de 1.37 KB. Ces violations existaient avant task-027 (commits précédents sur la branche, fichiers non touchés par cette US — vérifié via `git log` et `git diff --stat`).
- Decisions d'implémentation à signaler à `/review` :
  - **Regroupement par sujet normalisé** : la spec laisse le choix entre `inReplyTo` / `references` / `subject normalisé`. Le DTO Angular `MailDto` n'expose pas `inReplyTo` ni `references` (ils existent côté C# mais pas côté TypeScript), et la consigne « Aucune modification core/models » a été respectée. Le regroupement utilise donc une normalisation de `subject` (strip Re:/Fwd:/TR:/Fw:) + tri par `sentDate` desc (parité Blazor lorsque les en-têtes RFC-5322 manquent). Limite : deux fils non liés au même sujet exact se retrouvent regroupés. Acceptable selon la spec : « l'objectif business est : un mail qui a une réponse plus récente disparaît de la liste principale ; le compteur sur le root est correct ».
  - **`isExpandedFor(messageId)` exposé sur le service** : permet à `mail-list` de tester l'état déplié sans référencer `expandedThreadMessageId`, ce qui satisfait le grep audit DOD « matches uniquement dans `mail-state.service.ts` et son spec ».
  - **`threadChildren` computed déplacé sur le service** : côté UI, `mail-list` consomme un computed signal préparé par le service plutôt que de connaître la structure `MailThreadInfoDto`.
  - **Toast d'erreur** : implémenté via le token `MSS_SNACKBAR_SHOW` déjà utilisé par `notification-dispatcher`. Injection optionnelle pour ne pas casser les tests.
- DOD self-check (réalisable par commande) :
  - [x] `nx build mss-lib` 0 erreur
  - [x] `nx test mss-lib` 0 failure (105 tests verts)
  - [x] Service : `displayedMails`, `threadCounts`, `expandedThreadMessageId`, `expandedThreadInfo`, `isLoadingThread`, `expandThread()`, `collapseThread()` ✓
  - [x] Service : 5 tests Vitest verts (filtrage List vs Conversation, expandThread succès, collapseThread reset, gestion erreur API)
  - [x] `mail-list` : utilise `displayedMails` ; intercale les enfants après le root quand le fil est déplié ; rendu indenté
  - [x] `mail-header` : nouveaux inputs `threadCount` / `isExpanded` / `isLoadingThread` / `isThreadChild` + output `(toggleThread)` ; chip + bouton uniquement quand `threadCount > 1 && !isThreadChild`
  - [x] `mail-header` : 2 tests Vitest sur le chip et le toggle (rendu et masquage sur enfant)
  - [x] `data-testid` posés : `mail-list-row-thread-toggle`, `mail-list-row-thread-count`, `mail-list-row-thread-child`
  - [x] Réactivité signal-based via `MailStateService.userSettings` + computed `mailViewMode` ; effect dans le constructeur du service collapse les fils ouverts au passage `Conversation → List`
  - [x] Audit grep DOD :
    - `mailViewMode` → service.ts + spec + mail-list.ts + mail-list.html ✓
    - `expandedThreadMessageId` → uniquement service.ts + spec ✓
    - `isThreadChild` → mail-header.ts + mail-header.html + mail-list.html (+ mail-header.spec.ts du test) ✓
  - [x] Aucun changement sur `Api/Mail/`, `Dtos/`, `Client/Blazor/`, `devops`
- Observable behaviour items (deferred to manual test — HAG, règle 10) :
  - Bascule live du toggle settings recompose la liste sans rechargement manuel (signal propagation déjà en place via `state.userSettings.set`)
  - Réactivité visuelle du chevron + spinner pendant le chargement
  - Indentation visible des enfants de fil
  - Toast d'erreur si l'API `getThread` échoue
  - Cliquer sur une ligne enfant ouvre le mail (synthèse `MailDto` minimal depuis `MailThreadItemDto`)
- Code-only : **aucun commit, aucun push** — l'humain (Pascal) gère les opérations git Angular et la PR TFS.
- Next step : `/review task-027` (pas d'`api-mail` touché → `/sonar` skippé per agents/develop.md).

## PRs

- `client-angular` (code-only — humain gère commit/push TFS et ouverture PR). Liste des fichiers modifiés sur la branche `feature/nova-rewriting-mss-fixes-20260410` (uncommitted) :
  - `front/libs/mss/src/features/mail/services/mail-state.service.ts` (modifié)
  - `front/libs/mss/src/features/mail/services/mail-state.service.spec.ts` (nouveau)
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.ts` (modifié)
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.html` (modifié)
  - `front/libs/mss/src/features/mail/components/mail-header/mail-header.component.ts` (modifié)
  - `front/libs/mss/src/features/mail/components/mail-header/mail-header.component.html` (modifié)
  - `front/libs/mss/src/features/mail/components/mail-header/mail-header.component.scss` (modifié)
  - `front/libs/mss/src/features/mail/components/mail-header/mail-header.component.spec.ts` (modifié)
- Forge a re-validé build + test (mss-lib) avant la transition `done-*` :
  - `nx build mss-lib` ✓
  - `nx test mss-lib` ✓ — 12 fichiers, 105 tests verts

## Code Review Summary

Verdict : **APPROVED** — 8 fichiers revus, 2 suggestions non bloquantes, 0 issue bloquante.

### Files reviewed

- `mail-state.service.ts` — ✅ implémentation propre. Helpers `normaliseThreadSubject` + `threadItemToMail` module-private avec JSDoc. Signaux/computeds correctement séparés (state vs derived). Effect en constructeur pour le reset `Conversation → List`. `expandThread` collapse l'éventuel précédent avant de charger. Toast d'erreur via `MSS_SNACKBAR_SHOW` (injection optionnelle pour ne pas casser les tests externes).
- `mail-state.service.spec.ts` — ✅ 5 tests structurés, fixtures clean, mock `MssApiService`/`MSS_SNACKBAR_SHOW` via `TestBed.configureTestingModule`. Couvre filtrage List/Conversation, expandThread succès, collapseThread reset, erreur API.
- `mail-list.component.ts` — ✅ exposes des accessors readonly vers les signaux du service ; `isLeafExpanded` / `isLeafLoading` encapsulent l'accès à `expandedThreadMessageId` (audit grep DOD). `onToggleThread` route correctement vers `expandThread` ou `collapseThread`.
- `mail-list.component.html` — ✅ utilise `displayedMails` à la place de `filteredEmails` ; intercale les enfants après le root via `@for (child of threadChildren())` + `[isThreadChild]="true"`. `[attr.data-mail-view-mode]` sur le conteneur pour faciliter les E2E.
- `mail-header.component.ts` — ✅ nouveaux inputs/outputs ajoutés sans casser l'API existante. Getter `showThreadControls` factorise la condition d'affichage. `onToggleThread` `stopPropagation()` bien en place pour éviter de déclencher la sélection du mail.
- `mail-header.component.html` — ✅ chip + chevron dans la ligne 3 du sujet, conditionnés par `showThreadControls`. `aria-expanded` + `aria-label` localisés (« Déplier/Replier la conversation »). Spinner remplace l'icône pendant le chargement, sur le bouton lui-même comme la spec le demande.
- `mail-header.component.scss` — ✅ classes BEM (`mail-header--thread-child`, `mail-thread-count`, `mail-thread-toggle--expanded`). Indentation 40px sur les enfants + bordure gauche colorée. Variables CSS du design system utilisées (fallbacks défensifs en place).
- `mail-header.component.spec.ts` — ✅ 2 nouveaux tests pour le chip et le toggle. Couvre rendu visible (leaf) et masqué (child).

### Suggestions (non-blocking)

- **Regroupement par sujet normalisé** : la US laisse le choix au dev (spec : « par `subject` normalisé / `references` / `inReplyTo` »). Le `MailDto` Angular n'expose pas `inReplyTo` ni `references` (présents dans le JSON backend mais pas dans le type TS), et la consigne « Aucune modification core/models » a été respectée → fallback sur la normalisation de sujet (parité Blazor lorsque les en-têtes RFC-5322 manquent). Limite documentée dans le develop log : deux fils non liés au même sujet exact se retrouveront groupés. Si une amélioration est demandée, exposer `inReplyTo` / `references` côté `MailDto.ts` est une étape simple (le JSON les contient déjà).
- **`expandThread` re-charge sur même id** : si jamais `expandThread(id)` est appelée avec l'id déjà ouvert, l'API est ré-interrogée. Le call-site (`mail-list.onToggleThread`) gère le cas via `collapseThread()`, donc le chemin n'est pas atteint en pratique. Une garde défensive (early return si `isExpandedFor(id) && expandedThreadInfo() !== null`) éviterait l'appel en cas d'invocation directe future.

### Blocking Issues

Aucun.

## Merged

- **Date** : 2026-05-04
- **Pushable PRs merged** : aucun (task-027 est code-only sur `client-angular` uniquement — aucune PR GitHub à merger côté forge)
- **`client-angular`** : managed manually by the human (commit / push / PR / merge TFS hors visibilité forge)
- **CI develop** : N/A (pas de merge GitHub côté repos forge-automated)
- **Validation humaine** : flag `--i-tested` présent — Pascal a validé la US end-to-end selon les 8 vérifications du Manual Test Plan (mode List par défaut, bascule Conversation, déploiement d'un fil, déploiement d'un autre fil, collapse manuel, clic sur un enfant, bascule retour mode List, gestion erreur API).
