# /verify-visual — Vérification visuelle des écrans mobiles

Usage :
- `/verify-visual {task-id}` — **Mode A (chaîné)**. Invoqué par
  `/lint-mobile` dans le cycle autonome, avant `/review`. Capture chaque
  écran `client-mobile` touché par la task (Playwright headless, session
  factice, API mockée par fixtures — aucun backend, aucune donnée réelle),
  paire chaque capture avec sa référence Stitch, consigne un
  `## Visual verify log` dans la task (recopié par `/review` dans le body
  de la PR sous `## Vérification visuelle`), puis enchaîne `/review`.
- `/verify-visual {screen-name}` — **Mode B (stand-alone)**. Capture un
  écran (ex. `/verify-visual settings`), imprime le verdict + le PNG, exit.
- `/verify-visual --all` — **Mode C (rattrapage complet)**. Capture tous
  les écrans mappés de `screens.json` et rafraîchit l'état visuel global
  (habillage compris). Manuel, hors chaîne.

Deux sévérités :
- **Écran blanc / crash de navigation** → BLOQUANT : `questions/{task-id}.md`
  + halt (vraie régression runtime, invisible aux tests unitaires).
- **Écart esthétique vs Stitch, écran/API non mappé, panne outillage** →
  best-effort : logué, la chaîne continue. Le juge du design reste l'humain
  au HAG.

Read `agents/verify-visual.md` and execute the full playbook :

1. Pre-flight : mode, skip clean si client-mobile non touché ou aucun écran
   dans le `## Stitch design log` ; install Playwright au premier run
   (`tools/visual-verify/`).
2. Lancer `npm start` (Client/Mobile, port 4200) en arrière-plan — ou
   réutiliser un serveur déjà up (ne jamais tuer un serveur humain).
3. `node capture.mjs --screens ... --out Client/Mobile/e2e/screenshots/{task-id}`
   (un sous-répertoire par task — traçabilité figée, pas d'écrasement
   inter-tasks).
4. Verdict : exit 2 → questions + halt ; exit 1 → skip best-effort ;
   exit 0 → jugement de fidélité par lecture des deux images (capture vs
   référence Stitch), 1-2 lignes par écran, informatif.
5. Commit/push des PNG sur la branche feature, liens **pinnés au SHA du
   commit** (jamais à la branche — elle est supprimée au /merge) ; copie de
   chaque capture vers `Docs/epics/img/screens/client-mobile/{écran}.png` (**état visuel
   global de l'application**, dernier état connu par écran — intégré par
   `/tech-writer` dans la doc produit de l'EPIC) puis habillage **gabarit
   smartphone** via `frame.mjs` (cosmétique, rendu Material inchangé ;
   les captures par task restent brutes pour la comparaison Stitch) ; `## Visual verify log`
   dans la task, hand-off `/review {task-id}`.

## Rules

- Scope : `client-mobile` uniquement (v1). Outillage dans
  `tools/visual-verify/` (workspace, jamais dans les repos produits).
- Fixtures 100 % fictives — aucune donnée de santé, aucun backend contacté.
- Pas de diff pixel avec baseline (palier explicitement hors v1).
- HAG (règle 10) : n'ouvre pas de PR, ne merge jamais.
