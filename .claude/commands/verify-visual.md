# /verify-visual — Vérification visuelle des écrans mobiles

Usage :
> **Hors de la chaîne autonome depuis task-347** (décision humaine du 2026-09-29). Son seul
> cas bloquant, l'écran blanc ou le crash de navigation, est couvert par `/e2e`, qui parcourt
> les vrais écrans contre le vrai backend. `/verify-visual` reste disponible **à la demande** :
> captures pour une PR, comparaison au design Stitch, rafraîchissement de la galerie « État
> visuel » de la doc d'EPIC. Plus aucune étape ne l'invoque, et il n'enchaîne sur aucune.

- `/verify-visual {task-id}` — **Mode A (sur une task, à la demande)**. Capture chaque
  écran `client-mobile` touché par la task (Playwright headless, session
  factice, API mockée par fixtures — aucun backend, aucune donnée réelle),
  paire chaque capture avec sa référence Stitch, consigne un
  `## Visual verify log` dans la task (recopié par `/review` dans le body
  de la PR sous `## Vérification visuelle` si la PR est encore à ouvrir), puis rend la main.
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
   (`Tools/visual-verify/`).
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
   dans la task, hand-off `/e2e {task-id}`.

## ⏱️ Instrumentation (obligatoire)

Borne l'étape et mesure chaque commande coûteuse — c'est ce qui rend le coût
du cycle **mesuré** au lieu d'estimé :

```bash
Tools/timing/step.sh start --task {task-id} --step verify-visual
Tools/timing/measure.sh --task {task-id} --step verify-visual --repo {repo} \
    --cwd {repo-path} --kind {kind} -- {commande}
Tools/timing/step.sh end --task {task-id} --step verify-visual --status ok
```

- **Kinds de cette étape** : `restore` (`npm install`, `playwright install`), `build` (`--label ng-serve-boot` pour le démarrage du serveur), `capture`
- Le boot `ng serve` est le poste le plus lourd de cette étape : le mesurer est ce qui justifiera (ou non) de démarrer **un** serveur par run `/forge` au lieu d'un par task.
- `step.sh end` est appelé **aussi** quand l'étape skip proprement
  (`--status skipped --note "{raison}"`) ou fail-fast (`--status failed`) — un
  skip non mesuré est un trou dans le journal, pas une mesure à zéro.
- `measure.sh` est **transparent** : sortie et code retour inchangés, la
  commande est exécutée telle quelle (donc sûr autour du scanner Sonar et de
  `npm test -- --watch=false`). Une panne du harnais ne casse jamais l'étape.
- Protocole complet et vocabulaire des kinds : `Tools/timing/README.md`.

---
## Rules

- Scope : `client-mobile` uniquement (v1). Outillage dans
  `Tools/visual-verify/` (workspace, jamais dans les repos produits).
- Fixtures 100 % fictives — aucune donnée de santé, aucun backend contacté.
- Pas de diff pixel avec baseline (palier explicitement hors v1).
- HAG (règle 10) : n'ouvre pas de PR, ne merge jamais.

---

## ⛓️ Chaînage — aucun

Depuis task-347, `/verify-visual` est **hors de la chaîne autonome** : aucune étape ne l'invoque,
et il **n'invoque aucune étape**. Il s'exécute à la demande, écrit son log ou imprime son rapport,
puis rend la main. Un écran blanc ou un crash détecté se signale dans le rapport et dans
`questions/{task-id}.md` (Mode A) ; il n'arrête aucune chaîne, puisqu'il n'y en a pas.
