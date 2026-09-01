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
   dans la task, hand-off `/review {task-id}`.

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

## ⛓️ Chaînage — NE PAS INTERROMPRE

> Cette section est **opérationnelle**, pas descriptive. Elle a été ajoutée le
> 2026-08-04 parce que la chaîne s'arrêtait en pratique à chaque étape : les
> fichiers disaient « hand off to … » sans jamais ordonner d'appeler l'étape
> suivante, donc l'agent rédigeait un rapport et rendait la main. L'humain devait
> relancer « continue la chaîne » à chaque maillon — ce qui vide de son sens la
> boucle autonome.

**À la fin de cette étape, tu invoques immédiatement l'étape suivante via l'outil
`Skill`, dans le MÊME tour, sans rien demander et sans rapport intermédiaire.**

`Skill(review, "{task-id}")` — c'est-à-dire
`/review {task-id}`.

**Tu appelles l'outil `Skill` maintenant**, sans rapport intermédiaire. Le rapport
unique de fin de cycle est celui de `/review`.

### Les DEUX seuls arrêts légitimes

1. **Fail-fast** — un vrai blocage technique : `questions/{task-id}.md` est écrit,
   et tu t'arrêtes en le disant. Un plafond d'itérations atteint, un build
   irréparable, une ambiguïté métier. **Le budget de contexte conversationnel
   n'en est pas un.**
2. **Décision humaine explicitement requise** par le task file — un encadré
   « arbitrage humain requis » sur un point précis. Tu traites tout le reste,
   puis tu poses la question sur ce seul point.

### Ce qui n'est PAS un motif d'arrêt

- une étape qui **skippe** (repo non touché) : elle enchaîne quand même ;
- une étape **best-effort** dont il reste des findings : c'est son
  fonctionnement normal ;
- un flaky pré-existant identifié comme tel ;
- la longueur du travail déjà accompli dans le tour ;
- l'envie de faire valider une étape intermédiaire — **HAG (règle 10) est la
  seule barrière humaine, et elle est au merge de la PR, pas avant.**
