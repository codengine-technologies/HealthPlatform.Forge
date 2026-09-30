# conventions/e2e.md — Ce que la forge a appris sur ses tests de parcours

> **Portée** : les suites e2e headless, `Client/Mobile/e2e/specs/` (task-345) et
> `Client/Angular/front/e2e/mss-e2e/specs/` (task-346), et leur catalogue
> `Api/Mail/e2e/scenarios.yml`.
> **Lu par** : `/develop` avant d'écrire ou de modifier un test e2e (Step 6b), et par la revue de
> code de `/review`.
> **Alimenté par** : `/review`, qui ajoute une convention à chaque « vert qui ment » trouvé en revue ;
> `/e2e`, qui tient le registre des flaky et des quarantaines ; et toute task qui corrige un bug
> passé au travers du filet, qui ouvre une entrée « trou du filet ».
> **Règle d'or de la forge** (CLAUDE.md) : chaque défaut trouvé laisse une prévention. Ce fichier est
> l'endroit où les défauts des tests de parcours deviennent des consignes.

## Protocole d'alimentation

1. **Un « vert qui ment » trouvé en revue** : un test qui reste vert quand la fonctionnalité est
   cassée.
   - Au premier cas, créer l'entrée dans « Conventions actives », avec la mutation qui l'a prouvé.
   - En cas de récidive, incrémenter **Occurrences**.
   - Une récidive sur un test **frais** signale que ce fichier n'a pas été lu.
2. **Un test flaky relevé par `/e2e`** : ligne dans le « Registre des flaky ».
   - Troisième occurrence du même test : `/e2e` le signale dans son log, et `/review` le remonte au
     rapport de fin de cycle comme **task de stabilisation à ouvrir**.
3. **Une quarantaine** : posée par l'humain seul. `/e2e` la liste à chaque run, avec son âge.
   - Au-delà de **14 jours**, elle est signalée en tête du `## E2E log` et du rapport de fin de cycle.
4. **Un trou du filet** : un bug visible du médecin, trouvé par un humain, en recette ou en
   production, que `/e2e` n'a pas attrapé.
   - La task de correction ouvre une entrée dans « Trous du filet ».
   - Elle ajoute ou durcit le scénario qui l'aurait attrapé, et **le prouve rouge d'abord** sur le
     bug non corrigé.

## Format d'entrée

```markdown
### {slug} — {titre court}
- **Piège** : {ce qui laissait le test vert à tort}
- **Consigne** : {ce que /develop fait d'emblée}
- **Preuve** : {la mutation qui a fait tomber le test une fois la consigne appliquée}
- **Origine** : task-NNN
- **Occurrences** : {n}
```

---

## Conventions actives

### garde-de-port-ipv4-seul — Un port « libre » en IPv4 peut être tenu en IPv6
- **Piège** : l'orchestrateur Angular (`run.mjs`, `portBusy`) ne sonde que `127.0.0.1:4200`.
  Or `nx serve` en dev écoute sur `[::1]:4200`, et `https://localhost:4200` (`BASE_URL`,
  `APP_URL`) résout **d'abord** `::1`. Avec le serveur de dev de l'humain debout, le garde répond
  « libre ». Deux issues sont alors possibles : un `EADDRINUSE` confus, ou une suite qui joue contre
  le serveur de dev (sans proxy e2e) au lieu du sien.
- **Consigne** : un garde de port sonde **les deux** familles (`127.0.0.1` et `::1`). Avant de
  lancer une voie, `/e2e` contrôle les ports par `netstat` (toutes adresses), pas par l'outil
  lui-même.
- **Preuve** : constaté sur task-325. `netstat` montrait `[::1]:4200 LISTENING` (le `nx serve`
  de l'humain) pendant que le garde IPv4 n'aurait rien vu. Le correctif de `portBusy` reste à
  faire sur `client-angular` (code-only, par une task) ; la preuve attendue est un garde rouge
  avec un serveur écoutant sur `::1` seul.
- **Origine** : task-325
- **Occurrences** : 1

### etat-optimiste — Juger ce que le serveur a enregistré, pas ce que l'écran affiche
- **Piège** : lu, signalé, acquittement, suppression… Les deux clients mettent l'écran à jour
  **avant** l'appel serveur, et ne reviennent en arrière que sur erreur. Un appel jamais émis passe
  donc vert.
- **Consigne** : armer l'attente de la réponse **avant** le clic (`waitForResponse`), exiger
  `ok()`, puis **recharger** et relire l'état.
- **Preuve** : no-op sur `updateReadStatus`, `updateFlagStatus`, `recordBiologyAck`,
  `delete*` → exactement les parcours visés rouges.
- **Origine** : task-345, task-346
- **Occurrences** : 3

### absence-pendant-chargement — Une absence ne se lit qu'une fois la liste chargée
- **Piège** : `toBeHidden()` ou `toHaveCount(0)` passent pendant le spinner. Une suppression sans
  effet serveur restait verte, notamment dans un dossier vide comme Brouillons.
- **Consigne** : attendre la fin du chargement, ou une ancre qui n'existe qu'une fois la liste
  chargée (`.sig-empty`, `.mail-list-empty`), avant d'asserter une absence.
- **Preuve** : no-op `deleteDraft`, `deleteSignature` → DRAFT-001 et SIGNATURE-001 rouges.
- **Origine** : task-346
- **Occurrences** : 2

### isvisible-sans-attente — `isVisible({ timeout })` n'attend pas
- **Piège** : `isVisible()` rend l'état **instantané** et ignore son `timeout`. Un élément encore en
  chargement est lu « absent », et le test saute ou passe.
- **Consigne** : utiliser `locator.waitFor({ state })` ou un helper `isShown(locator, ms)`, jamais
  `isVisible({ timeout })`.
- **Preuve** : 29 occurrences corrigées ; les parcours concernés sont devenus déterministes.
- **Origine** : task-345
- **Occurrences** : 1

### headless-jamais-skip — En headless, une donnée seedée absente est une régression
- **Piège** : `if (!visible) return;`, `expect.soft` puis `return`, `test.skip`. Hérités du mode
  humain, ces gardes rendaient vert un parcours qui ne s'était pas joué.
- **Consigne** : en headless, `requireData` et `softSkip` **échouent** ; `check` y est l'assertion
  bloquante. Aucun `return` silencieux.
- **Preuve** : revues de task-345 (deux passages) : 15 parcours durcis.
- **Origine** : task-345
- **Occurrences** : 2

### fenetre-annulation — Une suppression est différée : laisser la fenêtre expirer dans l'app
- **Piège** : sur les deux clients, la suppression n'est envoyée qu'au bout de 6 s (fenêtre
  d'annulation). Recharger avant ce délai l'annule, et le mail « revient ».
- **Consigne** : attendre la fenêtre (`UNDO_WINDOW_ELAPSED_MS`, 7 s) **dans l'app**, puis
  recharger et vérifier.
- **Preuve** : COMPOSE-001 rouge sous no-op `deleteEmail`, vert une fois la fenêtre respectée.
- **Origine** : task-345, task-346
- **Occurrences** : 2

### selecteur-ambigu — Scoper un sélecteur à l'écran voulu
- **Piège** : un sélecteur de classe (`ion-title.inbox-title`) résout aussi le menu latéral : le
  mode strict échoue, ou un faux titre est lu.
- **Consigne** : scoper à la page (`#inbox-main …`, `.mail-detail-toolbar …`) ou filtrer par texte.
  Dans weda2, qui a peu de `data-testid`, s'appuyer sur un `id`, un `title` ou le nom d'une icône
  (`ds-icon[name=…]`), jamais sur la position.
- **Preuve** : FOLDER-001 (mobile) en strict mode ; les boutons de la barre du détail weda2 sans
  libellé.
- **Origine** : task-345, task-346
- **Occurrences** : 2

### geste-cache — Une action révélée par un geste doit être révélée par ce geste
- **Piège** : les options de swipe (brouillon, groupe) et les actions de ligne visibles au
  survol n'existent pas pour Playwright tant que le geste n'est pas joué.
- **Consigne** : helper `swipeRowOpen` (mobile) ou `hover()` (weda2) avant le clic, jamais un `force`.
- **Preuve** : DRAFT-001 (mobile) et MAIL-001/003 (weda2) rouges tant que le geste manquait.
- **Origine** : task-345, task-346
- **Occurrences** : 2

### session-non-persistee — weda2 rejoue le login à chaque chargement
- **Piège** : weda2 ne garde pas ses jetons. Un `page.goto` direct part au login : il se trompe de
  page ou rend blanc.
- **Consigne** : entrer une fois par `openMss` / `openInbox`, puis naviguer **dans l'app**
  (`pushState` + `popstate`). « Relu après rechargement » signifie un rechargement complet.
- **Origine** : task-346
- **Occurrences** : 1

### porte-valide-ses-entrees — Une porte bloquante refuse les entrées qui la rendraient verte à tort
- **Piège** : la porte `gate` rendait **vert** sur des entrées vides ou fausses. Sans aucun
  `--report`, tout était « non contrôlé » ou « listé ». Un vrai rapport passé en `--listed` voyait
  ses rouges ignorés.
- **Consigne** : un outil qui rend un verdict **bloquant** valide ses entrées avant de conclure. Un
  verdict ne tombe jamais par défaut sur « vert ». Il faut au moins un rapport exécuté, un listing
  ne doit contenir aucun test joué, et toute entrée incohérente est une panne d'outillage (code 2).
  Chaque branche de tolérance (divergence, quarantaine) a son test positif **et** son test négatif.
- **Preuve** : `Evaluate_ListingWithAPlayedTest_IsRefused`,
  `Evaluate_WithoutAnyExecutedReport_IsRefused` ; branche « test absent sous divergence » rouge
  sous mutation.
- **Origine** : task-347 (revue)
- **Occurrences** : 1

### temps-reel-deja-charge — Une donnée déjà présente au chargement ne prouve pas le temps réel
- **Piège** : le signalement d'urgence d'un message arrivé « en direct » était déjà posé quand l'app
  chargeait la ligne. Le bandeau s'affichait donc sans que le flux `TagsUpdated` n'y soit pour
  rien, et le parcours restait vert avec un écouteur SSE neutralisé.
- **Consigne** : un parcours temps réel prouve d'abord **l'absence** de l'effet au moment où
  l'écran l'aurait lu autrement, puis son **arrivée**. Pour les résultats d'analyse, le faux
  fournisseur IA retarde ses réponses de classification (`--tagging-delay-ms`, 5 s dans le profil
  e2e). La preuve s'appuie sur ce que seul le flux apporte : une notification, pas une ligne que le
  rafraîchissement périodique de weda2 (30 s) ramènerait aussi.
- **Preuve** : `TagsUpdated` ignoré dans l'app → E2E-LIVE-001 rouge sur « le signalement d'urgence
  arrive en temps réel », sur les deux clients.
- **Origine** : task-343
- **Occurrences** : 1

### mutation-non-servie — Une mutation qui ne compile pas laisse servir l'ancien code
- **Piège** : sous `ng serve` / `nx serve`, une mutation qui casse la compilation (`return` en tête
  qui rétrécit un type à `never`, variable devenue inutilisée → TS6133) laisse le serveur servir
  le **dernier bundle valide**. Le parcours joue alors le code précédent : vert, ou rouge pour une
  autre raison, et la preuve est fausse dans les deux cas.
- **Consigne** : après chaque mutation, attendre dans le journal du serveur de dev un **nouveau**
  « Application bundle generation complete » (et aucun `[ERROR]`) avant de jouer. Écrire la
  mutation pour qu'elle compile : `if (Date.now() > 0) { return }`, `void uid; void tags`.
- **Preuve** : M1/MA2 invalides lors des premiers essais (TS2339, TS6133), puis rouges sur
  l'assertion visée une fois servies.
- **Origine** : task-343
- **Occurrences** : 1

### predicat-de-reponse — Un prédicat de `waitForResponse` se lit comme du code, pas comme un texte
- **Piège** : une expression régulière littérale réécrite en ligne de commande est devenue
  `//api/v1/settings$/i`, c'est-à-dire un **commentaire**. Le prédicat acceptait alors tout POST,
  et l'étape « le réglage est enregistré » était verte sans rien vérifier. Deuxième piège sur la
  même ligne : weda2 poste sur `/api/v1/Settings`, avec une majuscule.
- **Consigne** : relire dans le fichier le prédicat d'attente après toute édition automatisée. Le
  comparer à l'URL **réelle** vue dans une trace (`i` si la casse varie). Exiger `ok()` sur la
  réponse obtenue.
- **Origine** : task-343
- **Occurrences** : 1

### ligne-de-biologie — Une ligne de biologie affiche le titre du document CDA, pas le sujet
- **Piège** : `rowBySubject` ne trouve pas un compte rendu de biologie : la liste affiche le titre
  du document CDA (« Compte rendu d'examens biologiques »), pas le sujet du mail.
- **Consigne** : désigner une ligne de biologie par son **uid** (`mail-row-{uid}` sur le mobile,
  `mail-row-subject-{uid}` sur weda2), obtenu du serveur. Réserver la désignation par sujet aux
  messages ordinaires.
- **Origine** : task-343
- **Occurrences** : 1

### preuve-par-mutation — Un test e2e n'est terminé qu'une fois prouvé rouge
- **Piège** : un test écrit contre l'app qui marche ne dit rien de sa capacité à échouer.
- **Consigne** : pour chaque test ajouté ou durci, planter un no-op dans l'appel qu'il protège,
  constater le rouge **sur l'assertion prévue**, puis annuler. Consigner la mutation dans le
  `## Develop log`.
- **Origine** : task-345, task-346, task-347, task-343
- **Occurrences** : 4

---

## Registre des flaky

*(tenu par `/e2e` : une ligne par test vert au second essai ; troisième occurrence du même test →
task de stabilisation proposée)*

| Test | Client | Occurrences | Dernière task | Cause connue |
|---|---|---|---|---|
| dossiers — naviguer vers Archive et Corbeille (E2E-FOLDER-001) | angular | 1 | task-347 | à établir — 1er essai : « le dossier INBOX est ouvert » (titre de liste absent au retour vers INBOX) |
| inbox — filtres Non lus / Lus / Tous et recherche (E2E-INBOX-001) | angular | 1 | task-343 | à établir — vert au 2e essai |
| détail — bascule texte brut / HTML (E2E-DETAIL-002) | mobile | 1 | task-192 | à établir — 1er essai : « mail sans corps affichable » (`mail-body-empty` reste affiché, le corps seedé n'apparaît pas dans les 15 s). Sur task-192 : rouge aux 2 essais d'un premier run, flaky au run suivant (3 échecs sur 4 essais) ; vert au 1er essai sur `develop` (1 run). Piste : course entre l'état « Aucun contenu » affiché pendant le chargement et le corps enrichi |

## Quarantaines

*(posées par l'humain seul ; listées par `/e2e` à chaque run ; signalées au-delà de 14 jours)*

| Test | Client | Task de correction | Posée le |
|---|---|---|---|
| *(aucune)* | | | |

## Trous du filet

*(un bug visible du médecin que `/e2e` n'a pas attrapé ; la task de correction ajoute le
scénario qui l'aurait attrapé, prouvé rouge sur le bug)*

| Bug | Trouvé par | Scénario ajouté / durci | Task |
|---|---|---|---|
| *(aucun à ce jour)* | | | |
