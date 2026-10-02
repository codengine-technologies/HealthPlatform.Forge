# agents/e2e.md — Étape `/e2e` : le filet de non-régression fonctionnel, bloquant

> **task-347, EPIC E018.** L'étape rejoue les **parcours du médecin** (suites headless des
> tasks 345 et 346) contre le vrai backend `e2e`, et confronte chaque client au **catalogue de
> scénarios** (`Api/Mail/e2e/scenarios.yml`). Elle **arrête la chaîne** si un parcours régresse
> ou si un client décroche du catalogue.

```
/start → /develop → /sonar → /lint-angular → /lint-mobile → /e2e → /review → /tech-writer
```

## Position et rôle

- Invoquée par `/lint-mobile` (ou par `/develop` quand aucun des repos de cleanup n'est touché).
- **Après** tous les fixes qualité (`/develop` §Q, `/sonar`, `/lint-*`) : `/review` valide exactement
  le code que `/e2e` a testé.
- **Bloquante, sans exemption.** Le seul arrêt « normal » de la chaîne avant `/review` qui ne soit
  pas un plafond d'itérations : un parcours rouge, un écart de parité, ou un outillage en panne. C'est
  un **fail-fast** au sens de la règle 13.
- **Ne corrige rien.** Comme `/review`, l'étape est en lecture seule sur le code : elle rejoue,
  constate, écrit le `## E2E log`, et bloque ou enchaîne.

## ⏱️ Instrumentation

```bash
Tools/timing/step.sh start --task {task-id} --step e2e
Tools/timing/measure.sh --task {task-id} --step e2e --repo client-mobile --cwd Client/Mobile \
    --kind e2e --label mobile -- npm run e2e:headless
Tools/timing/measure.sh --task {task-id} --step e2e --repo client-angular --cwd Client/Angular/front \
    --kind e2e --label angular -- npm run e2e:mss
Tools/timing/measure.sh --task {task-id} --step e2e --repo api-mail --cwd Api/Mail \
    --kind e2e --label gate -- dotnet {outil} gate …
Tools/timing/step.sh end --task {task-id} --step e2e --status ok|skipped|failed --note "…"
```

Le kind `e2e` couvre une **voie** entière (montage, suite, parité, démontage) et la porte. Un skip
se mesure aussi (`--status skipped`) : sinon on ne distingue plus « gratuit » de « pas mesuré ».

## Step 0 — Pré-flight : quelles voies ?

1. Task file `tasks/wip-{task-id}.md` présent. Sinon, abandon.
2. **Repos touchés** par la task — pas seulement listés : un repo listé sans aucun changement ne
   déclenche rien.
   - Repo poussable (`api-mail`, `client-mobile`, `dtos-mss`) : touché si sa branche
     `feat/{task-id}-*` (ou `fix/…`) diffère de `origin/develop`
     (`git -C {repo} diff --quiet origin/develop...HEAD` échoue), ou si l'arbre de travail est sale.
   - `client-angular` (code-only) : touché s'il est listé dans `**Repos**:` **et**
     `git -C Client/Angular status --porcelain -- front/` n'est pas vide. Lecture seule : aucune
     autre opération git.
3. **Règle 1 — déclenchement par voie** :

   | Voie | Jouée si la task a touché | Suite |
   |---|---|---|
   | mobile | `api-mail`, `client-mobile` ou `dtos-mss` | `Client/Mobile` : `npm run e2e:headless` |
   | angular | `api-mail`, `client-angular` ou `dtos-mss` | `Client/Angular/front` : `npm run e2e:mss` |

   - Une voie dont la **suite n'existe pas** est sautée **avec la mention explicite**, jamais en
     silence. Voie Angular : si `Client/Angular/front/e2e/mss-e2e/run.mjs` est absent, noter
     « suite Angular non livrée (task-346) », et la colonne `angular` de la matrice est reportée
     « non contrôlée (task-346) », **jamais** verte.
   - **Aucune voie** → skip propre : `step.sh end --status skipped --note "aucune voie touchée
     ({repos touchés})"`, `## E2E log` d'une ligne, puis chaînage vers `/review`.
4. **Règle 2 — code testé** : chaque voie tourne sur l'état **courant** de ses repos. Il n'y a
   **aucun checkout** dans cette étape :
   - `api-mail` et `client-mobile` sont sur la branche de la task quand la task les touche, et sur
     `develop` sinon. `/start` y a veillé ;
   - `client-angular` est sur la branche choisie par l'humain.
   - Le backend e2e est **toujours** construit depuis le checkout courant d'`Api/Mail`. Une task
     backend est donc testée par les deux voies avec **son** api-mail.

## Step 0 bis — Dépendances du client avant chaque voie

Une voie qui démarre sur un clone dont `node_modules` est en retard sur le `package-lock.json`
sort en **code 2** (« outillage ») sans rien prouver, alors que la cause est une installation à
refaire. Constaté le 2026-10-02 sur task-338 : `@playwright/test` déclaré dans
`Client/Angular/front/package.json`, absent de `node_modules`, la voie Angular a échoué après
87 s de montage.

Avant de lancer une voie, vérifier que le paquet est installé, et sinon restaurer les
dépendances avec la commande standard du repo (mesurée, kind `restore`) :

```bash
# Angular
[ -d Client/Angular/front/node_modules/@playwright/test ] || \
  Tools/timing/measure.sh --task {task-id} --step e2e --repo client-angular \
      --cwd Client/Angular/front --kind restore -- npm ci --no-audit --no-fund
# mobile
[ -d Client/Mobile/node_modules/@playwright/test ] || \
  Tools/timing/measure.sh --task {task-id} --step e2e --repo client-mobile \
      --cwd Client/Mobile --kind restore -- npm ci --no-audit --no-fund
```

`npm ci` ne touche que `node_modules` : aucun fichier suivi, aucune opération git, donc compatible
avec le mode code-only de `client-angular`. Un `npm ci` qui échoue reste une panne d'outillage
(bloquante, Step 4).

## Step 1 — Jouer les voies (séquentiellement, jamais en parallèle)

Les deux voies publient les mêmes ports (5052, 3993, 3465, 3143) : **une à la fois**. Chaque
orchestrateur monte son backend, seede, joue, contrôle la parité **de sa colonne**, puis démonte,
y compris sur échec ou Ctrl+C. Il ne retire que les conteneurs apparus pendant son run.

| Code retour de la voie | Signification | Suite |
|---|---|---|
| 0 | suite verte, parité de la colonne verte | continuer |
| 1 | rouge : test en échec **ou** écart de parité | continuer : le verdict est rendu par la porte (step 3), qui sait lire la quarantaine |
| 2 | **outillage** : Docker, AppHost, seed, serveur de dev, certificat, aucun rapport produit | **bloquant** (règle 4) → step 4, motif « outillage » |

Rapports à relever après chaque voie :

- mobile : `Client/Mobile/e2e/headless/out/report.json` (et `summary.json`) ;
- angular : `Client/Angular/front/e2e/mss-e2e/out/report.json` (et `summary.json`).

Les copier aussitôt, par exemple dans `$TEMP/forge-e2e/{task-id}/{client}-report.json`. Le run
suivant vide ces dossiers.

## Step 2 — Le client non touché : son listing

**Règle 11 — le contrôle tourne dès qu'une voie tourne, y compris sur le client que la task ne
touche pas.** C'est ce qui attrape « comportement changé sur le mobile, Angular resté à l'ancienne
version ». Le client non touché n'est **pas rejoué** : son **listing** Playwright suffit, avec les
identifiants et les versions de chaque test, sans rien exécuter.

```bash
# mobile non touché
cd Client/Mobile && E2E_HEADLESS=1 PLAYWRIGHT_JSON_OUTPUT_NAME=$TEMP/forge-e2e/{task-id}/mobile-listing.json \
  npx playwright test --config e2e/playwright.config.ts --list --reporter=json
# angular non touché (seulement si la suite existe)
cd Client/Angular/front && PLAYWRIGHT_JSON_OUTPUT_NAME=$TEMP/forge-e2e/{task-id}/angular-listing.json \
  npx playwright test --config e2e/mss-e2e/playwright.config.ts --list --reporter=json
```

## Step 3 — La porte : un seul verdict

**Catalogue** : celui de la branche de la task si `api-mail` est touché, sinon celui
d'`origin/develop`. Sans checkout :

```bash
git -C Api/Mail show origin/develop:e2e/scenarios.yml > $TEMP/forge-e2e/{task-id}/scenarios.yml
```

**Outil** : `Api/Mail/tests/mss.mail.e2e/bin/Debug/net10.0/mss.mail.e2e.dll`. Chaque voie le
construit.

```bash
rm -f $TEMP/forge-e2e/{task-id}/e2e-log.md   # jamais le log d'un run précédent
dotnet {outil} gate --catalog {catalogue} \
  --report mobile={rapport}  |  --listed mobile={listing} \
  --report angular={rapport} |  --listed angular={listing} \
  --out $TEMP/forge-e2e/{task-id}/e2e-log.md
```

**Codes de la porte** :
- **0** : vert ;
- **1** : rouge, les motifs sont dans `--out` ;
- **2** : **outillage**. Entrées refusées : aucun rapport exécuté, « listing » contenant un test joué,
  catalogue illisible. Aucun `--out` n'est écrit. Le 2 **bloque** comme un 1, motif « outillage ».

| La porte bloque (code 1) | La porte liste sans bloquer |
|---|---|
| tout écart de parité (règle 11) : scénario `requis` manquant, test sans identifiant, identifiant inconnu, version périmée | les tests **flaky** : verts au second essai (règle 5) |
| tout test rouge après `retries: 1`, **y compris un rouge déjà présent sur `develop`** (règle 3 : aucune exemption « flaky pré-existant ») | les tests **en quarantaine**, quel que soit leur résultat |
| une quarantaine qui ne cite pas sa task de correction | les **divergences temporaires** ouvertes |

### Quarantaine — posée par l'humain seul

La seule échappatoire à un rouge. **La forge ne pose jamais une quarantaine**, ni ne la retire. Dans
le test, l'humain ajoute un tag et une annotation qui cite la task de correction :

```ts
test('…', { tag: ['@E2E-INBOX-001', '@quarantaine'],
            annotation: [{ type: 'version', description: '1' },
                         { type: 'quarantaine', description: 'task-361' }] }, …)
```

Le test continue de tourner. Son résultat est listé à chaque run, et son échec ne bloque pas.

### Divergence temporaire — décidée par l'humain, déclarée au catalogue

Un comportement modifié sur un seul client est un **arbitrage explicite**, jamais un oubli. Il se
déclare dans `Api/Mail/e2e/scenarios.yml`, sur le scénario, pour le client concerné :

```yaml
    divergences:
      angular:
        raison: le filtre « Signalés » arrive sur weda2 avec la refonte de l'inbox
        tache: task-360
```

Le contrôle tolère alors, pour ce client seulement, une version périmée ou un test absent. Le
chargement du catalogue refuse une divergence :
- sans raison ;
- sans task au format `task-NNN` ;
- ou qui vise un client qui n'est pas `requis` pour ce scénario.

Les **deux sorties légitimes** d'un écart de parité sont des décisions de l'humain : ajouter le
client manquant aux `**Repos**` de la task et mettre son test à jour, ou déclarer une divergence.

## Step 4 — Bloquer (fail-fast, règle 13)

Si une voie sort en 2 (outillage), si la porte sort en 1 (régression ou parité), **ou si la porte
sort en 2** (outillage : entrées refusées) :

1. `questions/{task-id}.md` qui dit **explicitement** la nature du blocage :
   - **Régression** : les tests en échec (client, titre, scénario), l'extrait d'erreur Playwright
     et le chemin des traces (`…/out/test-results/…/trace.zip`, `error-context.md`) ;
   - **Parité** : les écarts de la porte, avec les deux sorties légitimes ci-dessus ;
   - **Outillage** : la voie, le code, le log (`…/out/logs/`), et le rappel que la non-régression
     **n'est pas prouvée**.
2. **Aucune donnée de santé** : les suites n'en manipulent pas (identité synthétique, corpus ANS).
   Recopier des **extraits** d'erreur, jamais un corps de mail ni un dump de page.
3. Le `## E2E log` est **quand même** écrit dans le task file, en rouge.
4. `step.sh end --status failed --note "{motif}"`, task laissée dans son état (`wip-*`),
   **chaîne arrêtée** : pas d'appel à `/review`.

## Step 5 — Démontage garanti (règle 9)

L'étape ne rend **jamais** la main avec un backend `e2e` debout, même après un échec. Chaque
orchestrateur démonte lui-même. L'étape le vérifie à la fin :

- ports 5052, 8100, 4200, 3993, 3465, 3143 libres ;
- `docker ps -a` sans conteneur `e2e-dovecot-*` ni `e2e-greenmail-*` créé par le run.

Un résidu est noté dans le `## E2E log`. Si une voie a été tuée, recréer `out/STOP` pour la
laisser se démonter.

## Step 6 — Avertissement « parcours touché sans scénario » (clause de DOD)

`/e2e` **signale**, sans bloquer, les écrans ou pages modifiés par la task **sans** spec e2e
modifié. C'est la ligne de DOD, vérifiée par `/review`, qui bloque. Concrètement, un fichier modifié
sous `Client/Mobile/src/app/**` (`*.page.*`, `*.component.html`) ou sous
`Client/Angular/front/libs/mss/src/**` (`*.component.html`), alors qu'aucun fichier de
`Client/Mobile/e2e/specs/` ni de `Client/Angular/front/e2e/mss-e2e/specs/` ne bouge.

## Step 7 — `## E2E log` (règles 6 et 12)

Section ajoutée **à la fin** du task file, reprise telle quelle par `/review` dans le body des PRs,
et par `/tech-writer` dans la doc de l'EPIC E018 :

```markdown
## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | client-mobile touché | ✅ verte | 22 verts, 0 flaky, 0 rouge, 0 quarantaine | 3 min 10 s |
| angular | non touchée — listing | 📋 listée | 22 tests listés | 12 s |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ {branche de la task | origin/develop}
- Quarantaines : aucune | {liste}
- Divergences ouvertes : aucune | {liste}
- Parcours touchés sans spec e2e modifié : aucun | {liste}
- Démontage : complet (ports libres, aucun conteneur e2e résiduel)

{corps rendu par `gate --out` : verdict, listes, matrice de parité}
```

## Step 7b — Amélioration continue du filet (règle d'or)

Après chaque run, `/e2e` tient à jour `conventions/e2e.md`, le seul fichier que cette étape écrit
en dehors du task file et de `questions/` :

- **Registre des flaky** : une ligne par test vert au second essai, avec le compteur incrémenté et
  la dernière task. **À la troisième occurrence** du même test, le `## E2E log` le signale en tête :
  « flaky récurrent → task de stabilisation à ouvrir ». `/review` le remonte au rapport de fin
  de cycle.
- **Quarantaines** : recopiées avec leur âge. **Au-delà de 14 jours**, une quarantaine est signalée
  en tête du `## E2E log` : un test en quarantaine ne protège rien, sa correction est due.
- **Divergences ouvertes** : listées avec leur task de résorption. Une divergence dont la task est
  `done` ou `archived`, mais toujours déclarée au catalogue, est signalée comme **à retirer**.
- **Coût** : la durée de chaque voie reste au journal (kind `e2e`). Une voie qui dépasse de 50 %
  sa médiane des 10 derniers runs est signalée, parce que c'est souvent un test qui s'est mis à
  attendre un délai.

`/e2e` ne corrige pas les tests : il **rend visibles** les faiblesses du filet. Ce sont `/po` et
`/develop` qui les résorbent, par des tasks.

## Step 8 — Chaînage (règle 13)

**Vert** (aucune voie n'a sorti 2, la porte est sortie en **0**, et son `--out` vient de **ce** run), ou **skip propre** :
`step.sh end`, puis **appel immédiat, dans le même tour**, de `Skill(review, "{task-id}")`, sans
rapport intermédiaire.

**Rouge** : step 4, et arrêt. C'est l'un des deux seuls arrêts légitimes de la chaîne.

## Règles

- **Bloquante, sans exemption** : un rouge sur `develop` bloque aussi ; seule la quarantaine
  (humaine) l'exempte.
- **Outillage en panne = bloquant** : la non-régression n'est pas prouvée.
- **Jamais de modification de code** ni de catalogue par cette étape ; jamais de quarantaine ni de
  divergence posée par la forge.
- **Jamais de git** sur `client-angular` (code-only) ; aucun checkout ailleurs.
- **Une voie à la fois** : même ports.
- **Aucune donnée de santé** dans `questions/`, le `## E2E log` ou les extraits recopiés.
- **HAG (règle 10) inchangé** : `/e2e` n'ouvre pas de PR et ne merge jamais.
