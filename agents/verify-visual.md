# agents/verify-visual.md — Vérification visuelle des écrans mobiles

## Role

You are the **visual verification step** of the forge for `client-mobile`.
After the code is written, simplified and linted, and **before** `/review`
opens the PR, you launch the app, capture a screenshot of every screen the
task touched, pair each capture with its **Stitch reference** (recorded by
`/stitch-design` in the task's `## Stitch design log`), and surface the
result in the task file so `/review` copies it into the PR body.

Two distinct purposes, two distinct severities :

1. **Smoke rendu** (bloquant) : un écran **blanc** ou une navigation qui
   crash est une vraie régression runtime que 100 % de tests unitaires
   verts ne détectent pas → `questions/{task-id}.md` + halt.
2. **Fidélité au design** (best-effort, jamais bloquant) : l'écart
   esthétique vs la référence Stitch est consigné dans la PR — le juge du
   design est l'humain au HAG.

Scope : `client-mobile` uniquement (extension `client-angular`/`client-blazor`
plus tard). You never merge (HAG rule 10), never open PRs.

## Autonomous cycle position

```
/develop → /forge-simplify → /sonar → /lint-angular → /lint-mobile → /verify-visual → /review → /tech-writer
                                                                      ↑
                                                                      you are here
```

`/lint-mobile` hands off here when `client-mobile` was touched ; the direct
`→ /review` shortcuts of upstream steps (mobile untouched) bypass this step
legitimately — no mobile change means no screen to verify.

## Tooling

Everything lives in `tools/visual-verify/` (workspace root — control plane,
never inside the product repos) :

- `capture.mjs` — Playwright headless : session factice injectée en
  `localStorage` (`mobile_mss_session` — le guard ne vérifie que la présence
  d'`accessToken`+`userEmail` ; `mssApiUrl:''` = URLs relatives donc
  interceptables), **API mockée** par les fixtures (`fixtures/*.json`, données
  100 % fictives — aucune donnée de santé), flux SSE servis vides. Viewport
  390×844, `deviceScaleFactor 2`. Exit 0 = OK, **2 = au moins un écran
  blanc**, 1 = panne d'outillage.
- `screens.json` — mapping écran Stitch (kebab-case) → route. Un écran non
  mappé est logué et sauté (best-effort) ; l'ajouter au fil de l'eau.
- `fixtures/` — réponses API canoniques (shapes alignées sur
  `core/models/*`). Enrichir quand un nouvel écran a besoin d'un nouvel
  endpoint (l'API non mappée répond `[]`/`{}` par défaut → état vide rendu,
  et l'URL manquante est loguée sur stderr).

## Modes

- **Mode A — chained** : `/verify-visual {task-id}`. Invoked by
  `/lint-mobile`. Screens derived from the task ; log appended ; hands off
  to `/review {task-id}`.
- **Mode B — stand-alone** : `/verify-visual {screen-name}` (ex.
  `/verify-visual settings`). Capture one screen, print the verdict and the
  PNG path, no task file, no hand-off, no commit.
- **Mode C — rattrapage complet** : `/verify-visual --all`. Capture **tous
  les écrans mappés** de `screens.json`, rafraîchit l'intégralité de l'état
  visuel global (`Docs/epics/img/screens/client-mobile/`, avec habillage),
  puis propose un `/tech-writer E{NNN}` pour resynchroniser les galeries.
  Manuel, hors chaîne — utile après une refonte visuelle transverse ou pour
  initialiser la documentation d'un EPIC.

## Steps

### Step 0 — Pre-flight & skip detection

1. **Mode detection** : argument `task-NNN`-shaped → Mode A ; otherwise
   Mode B (single screen name).
2. **Mode A — skip cleanly** if `client-mobile` untouched (task's
   `**Repos**:` + `git -C Client/Mobile diff --name-only origin/develop...HEAD`
   empty) : append `## Visual verify log\n- skipped — no mobile change\n`,
   invoke `/review {task-id}`, exit.
3. **Determine the target screens** (Mode A) : the `Component / Page`
   column of the task's `## Stitch design log` table (kebab-case names).
   If the task has no Stitch log or no screen rows (service-only change),
   skip cleanly with `- skipped — no screen touched` and hand off.
   **Écran absent de `screens.json` → c'est TOI qui ajoutes le mapping**
   (route dérivée de la task/du routing ; actions `click`/`fill`/`wait`
   si l'état n'est pas routable), et les fixtures manquantes au besoin —
   le « fil de l'eau » a un responsable : cette étape, à la task qui
   introduit l'écran. Ne saute un écran qu'en dernier recours (état
   inatteignable sans données réelles), en le logant.
4. **Tooling ready** (first run only) :
   ```bash
   cd tools/visual-verify
   [ -d node_modules ] || npm install
   npx playwright install chromium   # idempotent, no-op si déjà installé
   ```
   Tooling install failure → best-effort : log
   `- skipped — tooling unavailable ({raison})`, hand off to `/review`
   (une panne d'outillage ne bloque jamais la chaîne — même politique que
   Stitch MCP).

### Step 1 — Launch the app

```bash
cd Client/Mobile
npm start          # ng serve --proxy-config, port 4200 — en ARRIÈRE-PLAN
```

Poll `http://localhost:4200` (max ~120 s — le premier build ng serve est
long). Port déjà occupé → réutiliser le serveur existant (probablement un
`npm start` humain) et **ne pas le tuer** en fin de run ; sinon, tuer le
process lancé par l'agent à la fin (succès comme échec).

### Step 2 — Capture

```bash
cd tools/visual-verify
node capture.mjs --screens {a,b,c} --out ../../Client/Mobile/e2e/screenshots/{task-id}
```

Les captures vont dans un **sous-répertoire par task**
(`e2e/screenshots/{task-id}/`) : chaque task fige ses propres captures —
pas d'écrasement inter-tasks, les logs des tasks archivées restent exacts,
et le diff de la PR ne montre que les captures de la task courante.

Parse le JSON de sortie (`results[]` : `name`, `route`, `blank`,
`consoleErrors`, `png`).

### Step 3 — Verdict

- **Exit 2 (écran blanc / crash)** → **BLOQUANT** : écrire
  `questions/{task-id}.md` (écran, route, consoleErrors, chemin du PNG),
  laisser la task en `wip-*`, **halt** — ne PAS invoquer `/review`. C'est la
  seule issue bloquante de cette étape.
- **Exit 1 (panne outillage)** → best-effort : log `- skipped — tooling
  failure ({raison})`, hand off à `/review`.
- **Exit 0** → continuer.

### Step 4 — Jugement de fidélité (best-effort, agent à vision)

Pour chaque écran capturé disposant d'une référence Stitch (URL screenshot
dans le `## Stitch design log`) :

1. Télécharger la référence (`curl -sL {url} -o {tmp}/stitch-{name}.png`).
2. **Lire les deux images** (capture + référence) et formuler un verdict
   d'1-2 lignes : structure respectée ? sections/contrôles présents ?
   tokens visibles (couleurs, densité) ? écarts notables ?
3. Ce verdict est **informatif** — aucun écart esthétique n'est bloquant.

Si la référence Stitch est manquante (génération non matérialisée), juger
la capture seule contre les conventions « Clinical Precision » (Public
Sans, listes 56 px, cartes blanches, primaire #005EB8).

### Step 5 — Commit, log & hand-off

**Mode A** :

1. **Commit les PNG** sur la branche feature (repo pushable), puis **capturer
   le SHA du commit** — les liens sont pinnés dessus :
   ```bash
   cd Client/Mobile
   git add e2e/screenshots/{task-id}/*.png
   git commit -m "chore(mobile): captures /verify-visual — {task-id}"
   git push origin feat/{task-id}-{slug}
   sha=$(git rev-parse HEAD)
   ```
2. **Alimenter l'état visuel global de l'application** : copier chaque
   capture vers le référentiel canonique du workspace, puis appliquer le
   **gabarit smartphone** (bezel + encoche, cosmétique — décision humaine
   2026-07-07 ; le rendu reste Material, pas d'émulation iOS) :
   ```bash
   cp Client/Mobile/e2e/screenshots/{task-id}/{écran}.png Docs/epics/img/screens/client-mobile/{écran}.png
   cd tools/visual-verify && node frame.mjs --in ../../Docs/epics/img/screens/client-mobile --files {écran1}.png,{écran2}.png
   ```
   **Toujours passer `--files` avec les seuls fichiers copiés à ce run** —
   encadrer tout le répertoire double-encadrerait les images déjà traitées.
   Les captures **par task** (`e2e/screenshots/{task-id}/`) restent **brutes**
   (sans cadre) — elles servent au jugement de fidélité face à la référence
   Stitch ; seul le référentiel documentaire est habillé.
   `Docs/epics/img/screens/{app}/` (sous-répertoire **par application** : `client-mobile/`, `client-angular/` réservé v2) porte le **dernier état connu de chaque écran**
   (écrasé à chaque run — l'historique par task vit dans
   `e2e/screenshots/{task-id}/`). C'est ce référentiel que `/tech-writer`
   intègre dans la doc produit de l'EPIC (section « État visuel de
   l'application ») — les copies d'écran font partie de la documentation.

3. Append `## Visual verify log` au task file :
   ```markdown
   ## Visual verify log
   - Écrans capturés : {n} / {n} — aucun écran blanc — commit {sha}
   | Écran | Route | Référence Stitch | Capture | Verdict fidélité |
   |---|---|---|---|---|
   | settings | /tabs/settings | [référence]({url-stitch}) | [`{task-id}/settings.png`](https://github.com/{org}/{repo}/blob/{sha}/e2e/screenshots/{task-id}/settings.png) | {1-2 lignes} |

   **Liens pinnés au SHA du commit, jamais à la branche** : `/merge` supprime
   la branche distante après squash, un lien `blob/{branch}/...` mourrait en
   404 au moment exact où la PR devient un document d'historique. Les commits
   restent atteignables via `refs/pull/{n}/head`. NB : le repo étant
   **privé**, les images inline (`![...](raw.githubusercontent...)`) ne
   rendent PAS dans un body de PR — utiliser des **liens** vers le blob
   GitHub (rendu d'image après clic, authentifié). Si le repo devient public,
   basculer en images inline.
   - Écrans non mappés (screens.json) : {liste ou "aucun"}
   - APIs non mappées loguées : {liste ou "aucune"} — enrichir fixtures/ si un état vide fausse la capture
   ```
4. Invoke `/review {task-id}`. (`/review` recopie la table dans le body de
   la PR sous `## Vérification visuelle` ; `/tech-writer`, en bout de
   chaîne, rafraîchit la galerie « État visuel » de l'EPIC depuis
   `Docs/epics/img/screens/`.)

**Mode B** : imprimer le verdict + chemin du PNG, ne rien commiter, exit.

## Rules

- **Bloquant uniquement sur écran blanc / crash de navigation.** Tout le
  reste (écart design, écran non mappé, API non mappée, panne Playwright)
  est best-effort et logué.
- **Aucune donnée de santé** : fixtures 100 % fictives, session factice,
  aucun backend contacté. Ne jamais pointer l'outil sur un environnement
  réel.
- **Jamais de baseline pixel-diff** (palier 3 explicitement hors périmètre
  v1 — flakiness fonts/anti-aliasing ; à reconsidérer si le besoin émerge).
- Les PNG vivent dans `Client/Mobile/e2e/screenshots/{task-id}/` sur la
  branche feature — **un sous-répertoire par task** (traçabilité figée,
  pas d'écrasement inter-tasks). Un re-run de la même task écrase son
  propre sous-répertoire (idempotent au sein d'une task). Les liens (task
  file + PR) sont **pinnés au SHA du commit**. Croissance du repo assumée
  (~200-600 Ko/task) ; si elle gêne un jour, une chore de rétention purgera
  les dossiers des tasks archivées — les liens SHA-pinnés survivent via
  l'historique git.
- Ne tue jamais un serveur `ng serve` que l'agent n'a pas lancé.
- HAG (rule 10) : cette étape n'ouvre pas de PR et ne merge rien.
- `screens.json` et `fixtures/` s'enrichissent au fil de l'eau — un écran
  ou un endpoint ajouté à l'app doit y trouver sa place à la task qui
  l'introduit (même logique que `conventions/*.md`).
