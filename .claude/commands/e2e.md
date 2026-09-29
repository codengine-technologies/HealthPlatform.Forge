# /e2e — Filet de non-régression fonctionnel, bloquant

Usage : `/e2e {task-id}`. Invoqué par `/lint-mobile` dans le cycle autonome, avant `/review`.
Forme manuelle identique, par exemple pour rejouer après une correction.

Purpose : rejouer les **parcours du médecin** des suites headless (mobile : task-345, Angular :
task-346) contre le vrai backend `e2e`, confronter chaque client au **catalogue de scénarios**
(`Api/Mail/e2e/scenarios.yml`), et **arrêter la chaîne** si un parcours régresse ou si un client
décroche du catalogue. Écrit le `## E2E log` du task file, que `/review` recopie dans les PRs.

Read `agents/e2e.md` and execute the full playbook :

1. Pré-flight : repos réellement touchés, puis voies à jouer.
   - Voie mobile : `api-mail`, `client-mobile` ou `dtos-mss` touché.
   - Voie Angular : `api-mail`, `client-angular` ou `dtos-mss` touché, et suite présente. Sinon,
     noter « suite Angular non livrée (task-346) ».
   - Aucune voie : **skip mesuré**, puis `/review`.
2. Jouer les voies **une à la fois**, sur le checkout courant, sans aucune opération git :
   - mobile : `npm run e2e:headless` dans `Client/Mobile` ;
   - Angular : `npm run e2e:mss` dans `Client/Angular/front`.
   Chaque voie est enveloppée dans `measure.sh --kind e2e`. Un code 2 signale un problème
   d'outillage : l'étape bloque.
3. Client non touché : relever son **listing** (`playwright test --list`) pour la parité, sans le
   rejouer.
4. **Porte** :
   `dotnet mss.mail.e2e.dll gate --catalog … --report|--listed mobile=… --report|--listed angular=… --out …`.
   - Elle bloque sur un test rouge hors quarantaine, un écart de parité, ou une quarantaine sans
     task de correction.
   - Elle liste sans bloquer les tests flaky, les tests en quarantaine et les divergences ouvertes.
5. Vérifier le démontage : ports libres, aucun conteneur e2e résiduel.
6. Signaler, sans bloquer, les écrans modifiés sans spec e2e modifié.
7. Écrire le `## E2E log` : table des voies, puis verdict, listes et matrice de parité.
   - **Vert** → `/review`.
   - **Rouge** → `questions/{task-id}.md`, avec la nature du blocage (régression, parité ou
     outillage), et arrêt.

## ⏱️ Instrumentation (obligatoire)

Borne l'étape et mesure chaque commande coûteuse — c'est ce qui rend le coût
du cycle **mesuré** au lieu d'estimé :

```bash
Tools/timing/step.sh start --task {task-id} --step e2e
Tools/timing/measure.sh --task {task-id} --step e2e --repo {repo} \
    --cwd {repo-path} --kind e2e --label {mobile|angular|gate} -- {commande}
Tools/timing/step.sh end --task {task-id} --step e2e --status ok
```

- **Kind de cette étape** : `e2e` (une voie entière — montage, suite, parité, démontage — et la porte).
- `step.sh end` est appelé **aussi** quand l'étape skip proprement
  (`--status skipped --note "{raison}"`) ou fail-fast (`--status failed`) — un
  skip non mesuré est un trou dans le journal, pas une mesure à zéro.
- `measure.sh` est **transparent** : sortie et code retour inchangés.
- Protocole complet et vocabulaire des kinds : `Tools/timing/README.md`.

---
## Rules

- **Bloquante, sans exemption** : un rouge après `retries: 1` bloque, y compris un rouge déjà présent
  sur `develop`. La seule échappatoire est la **quarantaine**, que **seul l'humain** pose (tag
  `@quarantaine` + annotation citant la task de correction).
- **Outillage en panne = bloquant** : la non-régression n'est pas prouvée. Le `questions/`
  distingue « outillage », « régression » et « parité ».
- **Parité bloquante** : tout écart bloque. Il n'y a que deux sorties légitimes, décidées par
  l'humain : ajouter le client aux `**Repos**` et mettre son test à jour, ou déclarer une
  **divergence temporaire** au catalogue (raison + task de résorption).
- Lecture seule : la forge ne corrige rien, ne pose ni quarantaine ni divergence, ne touche jamais
  git sur `client-angular`, et ne fait aucun checkout.
- Une voie à la fois (mêmes ports). Démontage vérifié avant de rendre la main.
- Aucune donnée de santé dans `questions/` ni dans le `## E2E log`.
- HAG (règle 10) : n'ouvre pas de PR, ne merge jamais.

---

## ⛓️ Chaînage — NE PAS INTERROMPRE

> Cette section est **opérationnelle**, pas descriptive. Elle a été ajoutée le
> 2026-08-04 parce que la chaîne s'arrêtait en pratique à chaque étape : les
> fichiers disaient « hand off to … » sans jamais ordonner d'appeler l'étape
> suivante, donc l'agent rédigeait un rapport et rendait la main. L'humain devait
> relancer « continue la chaîne » à chaque maillon — ce qui vide de son sens la
> boucle autonome.

**À la fin de cette étape, si elle est verte ou skippe proprement, tu invoques immédiatement
l'étape suivante via l'outil `Skill`, dans le MÊME tour, sans rien demander et sans rapport
intermédiaire.**

`Skill(review, "{task-id}")` — c'est-à-dire
`/review {task-id}`.

**Tu appelles l'outil `Skill` maintenant**, sans rapport intermédiaire. Le rapport
unique de fin de cycle est celui de `/review`.

### Les DEUX seuls arrêts légitimes

1. **Fail-fast** — un vrai blocage technique : `questions/{task-id}.md` est écrit,
   et tu t'arrêtes en le disant. **Un parcours rouge, un écart de parité ou un
   outillage en panne à cette étape en sont un.** Un plafond d'itérations
   atteint, un build irréparable, une ambiguïté métier aussi. **Le budget de
   contexte conversationnel n'en est pas un.**
2. **Décision humaine explicitement requise** par le task file — un encadré
   « arbitrage humain requis » sur un point précis. Tu traites tout le reste,
   puis tu poses la question sur ce seul point.

### Ce qui n'est PAS un motif d'arrêt

- une étape qui **skippe** (aucune voie touchée) : elle enchaîne quand même ;
- un test **flaky** (vert au second essai) : il est listé, pas bloquant ;
- un test **en quarantaine** : il est listé, pas bloquant ;
- la longueur du travail déjà accompli dans le tour ;
- l'envie de faire valider une étape intermédiaire — **HAG (règle 10) est la
  seule barrière humaine, et elle est au merge de la PR, pas avant.**
