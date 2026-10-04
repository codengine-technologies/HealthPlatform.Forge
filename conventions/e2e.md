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
- **Variante .NET (task-349)** : les analyseurs Sonar du build `client-blazor` refusent une
  mutation triviale (`if (false)` → S4487 champ jamais lu, `x.Length < 0` → S3981). Le build
  échoue, aucun test ne tourne, et un filtre sur « Passed!/Failed! » n'affiche **rien** : la
  mutation a l'air sans effet. Prédicat opaque aux analyseurs : `Environment.TickCount64 < 0`
  (C#), `Date.now() < 0` (TS).
- **Origine** : task-343, task-349
- **Occurrences** : 2

### predicat-de-reponse — Un prédicat de `waitForResponse` se lit comme du code, pas comme un texte
- **Piège** : une expression régulière littérale réécrite en ligne de commande est devenue
  `//api/v1/settings$/i`, c'est-à-dire un **commentaire**. Le prédicat acceptait alors tout POST,
  et l'étape « le réglage est enregistré » était verte sans rien vérifier. Deuxième piège sur la
  même ligne : weda2 poste sur `/api/v1/Settings`, avec une majuscule.
- **Consigne** : relire dans le fichier le prédicat d'attente après toute édition automatisée. Le
  comparer à l'URL **réelle** vue dans une trace (`i` si la casse varie). Exiger `ok()` sur la
  réponse obtenue.
- **Récidive (task-348)** : `E2E-SEARCH-001` (Angular) attendait « toute requête dont l'URL contient
  `/api/v1/search/` ». Le client appelle aussi `GET /search/history`, parti 10 ms avant le `POST
  /search/semantic` dans une trace : le test capturait l'historique (sans corps) et lisait « la
  requête ne porte pas les termes ». Flaky, puis rouge, selon l'ordre des requêtes.
- **Consigne (ajoutée)** : un prédicat d'attente fixe la **méthode** et le **chemin exact** de
  l'endpoint attendu (`r.method() === 'POST' && /\/search\/semantic$/i.test(pathname)`), jamais un
  préfixe partagé par plusieurs routes.
- **Origine** : task-343, task-348
- **Occurrences** : 2

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

### ancre-conditionnelle — L'ancre « contenu chargé » doit exister dans tous les cas du parcours
- **Piège** : pour lire l'absence du bandeau de rattachement après rechargement, le test Angular
  attendait l'indicateur « rattaché » de l'onglet du document. Or weda2 n'affiche des onglets que
  pour un message à **plusieurs** documents : avec un seul, l'ancre n'existe jamais, et le test
  tombait sur l'attente alors que l'écran était juste.
- **Consigne** : une ancre de chargement est un élément rendu **sans condition** une fois la donnée
  arrivée, et alimenté par la **même source** que ce dont on lit l'absence (ici `mss-mail-body`,
  qui reçoit `mailContent()` comme le bandeau). Vérifier dans le template qu'aucun `@if` ne la
  conditionne à autre chose que le chargement.
- **Preuve** : constaté en preuve par mutation sur task-331 (le parcours restauré restait rouge sur
  l'ancre). Avec `mss-mail-body .mail-body`, vert sur un seed neuf.
- **Origine** : task-331
- **Occurrences** : 1

---

### precondition-du-negatif — Une assertion d'absence ne prouve rien sans la présence d'avant
- **Piège** : « la citation n'est pas envoyée » est restée verte alors que la citation n'avait
  jamais été dans le message. Le transfert, cliqué 80 ms après l'ouverture du mail, était parti
  sans contenu. Une absence se vérifie aussi quand la chose n'existe pas : le test ne voyait ni le
  bug du transfert, ni ce qu'il croyait protéger.
- **Consigne** : toute assertion d'absence (« X n'est pas envoyé », « X n'est pas modifié ») est
  précédée de l'assertion de sa **présence** dans l'état de départ. Exemple : la citation est dans
  l'éditeur avant de demander la correction.
- **Preuve** : à faire avec le correctif du transfert. Retirer la citation du préremplissage doit
  faire tomber le test sur la précondition, pas plus loin.
- **Origine** : task-349 (/e2e, 2026-10-01)
- **Occurrences** : 1

### depot-hors-application — Un message déposé hors de l'app n'apparaît qu'à une relecture du dossier
- **Piège** : un message déposé directement en IMAP (outil `message --create`, relais `deliver`)
  n'est vu par l'application qu'à la prochaine relecture **réelle** du dossier. L'état du dossier
  est en cache (statut 10 s), et le rafraîchissement de la liste passe toutes les 30 s. Un unique
  `toBeVisible({ timeout: 30000 })` tombe donc pile sur la limite. Il est vert en `--serve-only` à
  froid, et rouge dans la suite complète, où la liste vient d'être lue.
- **Consigne** : attendre un dépôt hors de l'application en **rouvrant la boîte jusqu'à son
  arrivée** (`expect.poll` + `openInbox`, 90 s, pas de 3 s), comme E2E-COMPOSE-001 ; côté mobile,
  `waitForSubject`. Jamais une seule attente passive bornée à l'intervalle de rafraîchissement.
- **Preuve** : E2E-MAIL-005 (Angular), rouge aux deux essais dans la suite complète du
  2026-10-04 (« le message déposé est dans la liste », 30 s), vert seul à froid.
- **Origine** : task-353
- **Occurrences** : 1

### suite-e2e-non-compilee — Ni le build ni les tests unitaires ne compilent les specs e2e
- **Piège** : les specs Playwright vivent hors du build de l'app (`tsconfig` isolé). Une erreur de
  syntaxe y passe donc `npm run build`, `npm test` et le lint, et ne se voit qu'au lancement de la
  voie, qui tombe **entière** en outillage. Sur task-352, la même faute dans les deux clients : un
  libellé français entre apostrophes simples qui contient une apostrophe
  (`'la boîte de réception s'affiche'`).
- **Consigne** : après toute écriture de spec e2e, compiler la suite avant de commiter :
  `npx tsc -p e2e/tsconfig.json` (mobile, depuis `Client/Mobile`) et
  `npx tsc -p e2e/mss-e2e/tsconfig.json` (Angular, depuis `Client/Angular/front`). **Les deux
  suites, chacune.** Les libellés français s'écrivent entre **guillemets doubles**.
  `agents/develop.md` Step 6b.5 l'exigeait déjà. Sur task-352, seule la suite mobile avait été
  compilée, et la faute Angular n'a été vue qu'à la passe qualité. Il s'agit d'une récidive de
  lecture (règle d'or 3), pas d'un trou du playbook.
- **Preuve** : les deux `tsc` rouges (TS1005, chaîne non terminée) sur le code fautif, verts
  après correction.
- **Origine** : task-352
- **Occurrences** : 2 (une par client, même task)

### test-angular-non-commite — Un scénario requis côté Angular repose sur un test que la forge ne commite pas
- **Piège** : en mode code-only, le test Angular d'un nouveau scénario reste **non commité** sur
  l'arbre de l'humain. Le catalogue, lui, part sur `develop` avec la PR api-mail. Si l'arbre Angular
  est ensuite nettoyé, remis à zéro ou changé de branche avant le commit TFS, le test disparaît.
  Le scénario reste `requis`, et **toutes** les tasks suivantes qui touchent `api-mail` bloquent à
  `/e2e` sur une parité rouge qui ne les concerne pas. Constaté sur task-341 : `E2E-MAIL-005`
  (ajouté par task-353) n'était dans aucun commit ni stash du clone Angular.
- **Consigne** : quand une task ajoute ou monte un scénario requis pour `angular`, `/review` le
  signale **en tête** du rapport de fin de cycle et dans le body de la PR api-mail : « à commiter
  sur TFS **avant** le merge de la PR api-mail : `functional.e2e.ts` (scénario …) ». Au `/e2e` d'une
  task suivante, un `MissingRequired` côté angular est d'abord cherché dans l'historique
  (`git log --all -S {id}`, stash) avant tout autre diagnostic.
- **Preuve** : porte rouge `MissingRequired [angular] E2E-MAIL-005` au 1er passage de task-341,
  puis verte une fois le test restauré (`8a288e97`).
- **Origine** : task-341 (héritage de task-353)
- **Occurrences** : 1

---

## Registre des flaky

*(tenu par `/e2e` : une ligne par test vert au second essai ; troisième occurrence du même test →
task de stabilisation proposée)*

| Test | Client | Occurrences | Dernière task | Cause connue |
|---|---|---|---|---|
| dossiers — naviguer vers Archive et Corbeille (E2E-FOLDER-001) | angular | 1 | task-347 | à établir — 1er essai : « le dossier INBOX est ouvert » (titre de liste absent au retour vers INBOX) |
| inbox — filtres Non lus / Lus / Tous et recherche (E2E-INBOX-001) | angular | 1 | task-343 | à établir — vert au 2e essai |
| détail — bascule texte brut / HTML (E2E-DETAIL-002) | mobile | 2 | task-338 | à établir — 1er essai : « mail sans corps affichable » (`mail-body-empty` reste affiché, le corps seedé n'apparaît pas dans les 15 s). Sur task-192 : rouge aux 2 essais d'un premier run, flaky au run suivant (3 échecs sur 4 essais) ; vert au 1er essai sur `develop` (1 run). Piste : course entre l'état « Aucun contenu » affiché pendant le chargement et le corps enrichi. Récidive sur task-338 (rouge au 1er essai, vert au 2e), task qui ne touche pas la lecture d'un message : le soupçon porté sur task-192 est levé, l'instabilité est propre au test |
| assistant — résumé initial puis deux questions de suite (E2E-AI-001) | angular | 2 | task-352 | à établir — task-338, 1er essai : `locator.click` en dépassement (15 s), puis `page.waitForResponse: Test ended`. task-352, 1er essai : `response.json: Protocol error (Network.getResponseBody): No data found for resource` (le corps de la réponse attendue n'est plus lisible par le navigateur quand le test le lit). Vert au 2e essai les deux fois. Voie Angular sur `feature/nova-rewriting-mss`. Piste : lire le corps par `waitForResponse` puis `await response.json()` sans délai, ou relire la conversation au serveur plutôt que dans la réponse |

| rédaction — corriger l'orthographe, appliquer, envoyer (E2E-COMPOSE-002) | angular | 3 | task-353 | **établie, ce n'est pas un flaky** : « Transférer » cliqué avant le chargement du contenu → transfert sans le message d'origine (`initializeFromPrefill` ne cite que `if (prefill.content)`). Reproduit 1/5 au premier passage à froid. Bug produit, voir Trous du filet (task-350). task-353 : de nouveau au 1er essai sur deux passages ; au 2e essai d'un passage, **incident de banc distinct** : rafale de connexions IMAP coupées à l'authentification (10053/10054, Seq 12:20:29 UTC), `enrich/sync` puis contenu en 503 → « Aucun contenu ». Piste : `mail_max_userip_connections` (10, défaut Dovecot du banc) atteint par des requêtes simultanées du même praticien |

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
| Transférer (et Répondre, même chemin) cliqué avant le chargement du contenu du mail : le message part **sans le message d'origine**, sans erreur visible | /e2e task-349 (E2E-COMPOSE-002, 1er passage à froid) | E2E-DETAIL-001 à durcir : le transfert relu côté serveur porte la citation ; précondition ajoutée à E2E-COMPOSE-002 (dans task-349) | task-350 |
| Un message rédigé plus de 30 s (brouillon enregistré automatiquement) part **sans ses pièces jointes**, sans accusé de lecture ni acquittement d'opposition, « envoyé » affiché (Angular et Blazor : route des brouillons dès qu'un brouillon existe) | Audit de bugs du 2026-09-27 (AUD-06), non vu par `/e2e` : aucun scénario n'envoyait un brouillon, ni une pièce jointe | **E2E-DRAFT-002** ajouté (mobile et Angular requis) : la pièce jointe est relue dans le message **reçu**, après l'enregistrement automatique. Rouge sur les deux clients avec le bug réinjecté côté serveur | task-329 |
| Un document sans INS dont les traits ne correspondent à aucune fiche (ou sans trait) ne peut **pas être rattaché** : le dialogue n'offre que les candidats de `/patients/match`, puis « Ignorer » (Angular, Blazor, mobile) | L'humain au HAG de task-331, non vu par `/e2e` : aucun scénario ne rattachait un document à la main | **E2E-PATIENT-002** ajouté (mobile et Angular requis) : document sans INS seedé, aucun candidat, recherche libre, confirmation, message relu dans le dossier de la fiche. Rouge sous mutation (confirmation sans appel) sur les deux clients | task-331 |
| Un dossier supprimé ou renommé depuis un autre logiciel de messagerie, puis ouvert dans l'app : **chargement sans fin** (Angular), anciens messages affichés (Blazor), message technique brut (mobile). Le serveur répondait 404 sans nommer la cause | L'humain, en recette (Seq : `GET /folders/…` → 404), non vu par `/e2e` : aucun scénario ne modifiait la boîte hors de l'application | **E2E-FOLDER-003** ajouté (mobile et Angular requis) : dossier créé dans l'app, supprimé par IMAP (`mss.mail.e2e folder --delete`), puis ouvert. Rouge sur les deux clients avec le bug réinjecté (Angular : spinner sans fin reproduit) | task-352 |
| Un message supprimé ou déplacé depuis un autre logiciel **reste dans la liste** (rafraîchissement aveugle aux disparus) et s'ouvre sur un **contenu vide ou périmé** servi par la ligne locale (200, aucun accès IMAP) | L'humain, en recette (Seq : `GET …/emails/content/10` → 200 en 20 ms), non vu par `/e2e` : aucun scénario ne supprimait un message hors de l'application | **E2E-MAIL-005** ajouté (mobile et Angular requis) : message déposé puis supprimé par IMAP (`mss.mail.e2e message --create|--delete`), ouvert aussitôt (« n'existe plus », jamais vide), puis retiré au rafraîchissement. Rouge sous mutation sur les deux clients, et sur chacune des deux branches côté Angular (ouverture, rafraîchissement) | task-353 |

---

### attente-satisfaite-par-un-placeholder — « visible » n'est pas « chargé » quand un élément vide porte le même testid
- **Piège** : pour attendre le corps du mail, `E2E-DETAIL-002` (mobile) attendait
  `mail-body-html` ou `mail-body-plain` **visible**. Pendant le chargement (détail ouvert avec le
  `MailDto` de la liste, contenu pas encore arrivé), le composant rendait un `<pre
  data-testid="mail-body-plain">` **vide**, que son padding rend « visible », **et** l'état
  « Aucun contenu disponible ». L'attente passait à 50 ms, avant toute réponse, et le contrôle
  suivant voyait l'état vide. Le test était rouge selon la vitesse du contenu (3/3 sur la
  combinaison task-331 + task-348, vert sur chacune seule), et l'écran montrait vraiment un
  courrier vide pendant un instant.
- **Consigne** : une attente de chargement porte sur le **contenu attendu**, pas sur la
  visibilité d'un conteneur : `toContainText(/\S/)` ou le texte seedé. Un `toBeVisible()` ne
  suffit jamais sur un élément qui peut être rendu vide. Côté composant, un état « vide » ne se
  rend que sur une donnée **chargée** et vide, et un placeholder de chargement a son propre
  `data-testid` (`mail-body-loading`).
- **Preuve** : test de composant « squelette pendant le chargement, ni état vide ni corps vide »
  rouge sur l'ancien `mail-body` (`squelette: Expected null not to be null`), vert après.
  `E2E-DETAIL-002` rouge 3/3 en `--serve-only` avant, vert après.
- **Origine** : task-348
- **Occurrences** : 1
