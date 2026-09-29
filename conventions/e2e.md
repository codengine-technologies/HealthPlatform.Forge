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

### preuve-par-mutation — Un test e2e n'est terminé qu'une fois prouvé rouge
- **Piège** : un test écrit contre l'app qui marche ne dit rien de sa capacité à échouer.
- **Consigne** : pour chaque test ajouté ou durci, planter un no-op dans l'appel qu'il protège,
  constater le rouge **sur l'assertion prévue**, puis annuler. Consigner la mutation dans le
  `## Develop log`.
- **Origine** : task-345, task-346, task-347
- **Occurrences** : 3

---

## Registre des flaky

*(tenu par `/e2e` : une ligne par test vert au second essai ; troisième occurrence du même test →
task de stabilisation proposée)*

| Test | Client | Occurrences | Dernière task | Cause connue |
|---|---|---|---|---|
| dossiers — naviguer vers Archive et Corbeille (E2E-FOLDER-001) | angular | 1 | task-347 | à établir — 1er essai : « le dossier INBOX est ouvert » (titre de liste absent au retour vers INBOX) |
| inbox — filtres Non lus / Lus / Tous et recherche (E2E-INBOX-001) | angular | 1 | task-343 | à établir — vert au 2e essai |

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
