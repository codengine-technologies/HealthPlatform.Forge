# Tools/timing — instrumentation du cycle de la forge

> **Pourquoi.** Avant cet outillage, personne ne mesurait quoi que ce soit :
> l'analyse du coût d'un cycle se faisait en comptant les commandes prescrites
> par les playbooks (« ~13 builds et ~11 suites de tests pour une task
> backend »), pas en mesurant la réalité. Toute optimisation était donc un pari.
> Ce harnais transforme les paris en mesures : combien de builds, combien de
> suites, combien de temps, par étape et par repo.

## Ce que ça mesure

Deux granularités, un seul journal :

| Événement | Émis par | Répond à |
|---|---|---|
| `type=step` | `step.sh start` / `step.sh end` | combien de temps dure `/develop`, `/sonar`, … et avec quel statut (ok / skipped / failed) |
| `type=cmd` | `measure.sh` | combien de builds / suites de tests / scans une étape consomme réellement, et ce que chacun coûte |

Journal : **`metrics/timings.jsonl`** — une ligne JSON par événement,
append-only, versionné (c'est le journal de mesure de la forge, comme les task
files sont son journal de travail).

## Les trois commandes

```bash
# 1. borner une étape
Tools/timing/step.sh start --task task-183 --step develop
Tools/timing/step.sh end   --task task-183 --step develop --status ok

# 2. mesurer une commande coûteuse (build, test, scan, lint, capture…)
#    --cwd remplace le `cd {repo}` : on reste à la racine du workspace
Tools/timing/measure.sh --task task-183 --step develop --repo api-mail \
    --cwd Api/Mail --kind build -- dotnet build HealthPlatform.Api.Mail.sln

# 3. lire les résultats
Tools/timing/report.sh --task task-183          # coût d'un cycle
Tools/timing/report.sh --task task-183 --sync   # écrit ## Timings dans le task file
Tools/timing/report.sh --last 10                # les 10 derniers cycles
Tools/timing/report.sh --by-kind                # LE tableau d'optimisation
```

### `measure.sh` est transparent

C'est la propriété qui rend le câblage sans risque :

- **stdout/stderr ne sont pas capturés** — l'agent voit la sortie du compilateur
  et des tests exactement comme sans le wrapper ;
- **le code de sortie est propagé** — les chaînes `&&` et la logique RED/GREEN
  des playbooks continuent de fonctionner à l'identique ;
- **la commande est exécutée directement** (`"$@"`), donc la conversion
  d'arguments MSYS et l'environnement exporté (`MSYS_NO_PATHCONV`,
  `SONAR_TOKEN`, …) se comportent comme en appel direct. C'est ce qui rend
  légitime d'envelopper `dotnet sonarscanner begin` ;
- **une panne de l'instrumentation ne casse jamais la commande** — tous les
  chemins d'erreur du harnais sortent en 0 et écrivent au mieux.

Tout ce qui suit le **premier** `--` est la commande, verbatim : les `--`
suivants sont préservés (indispensable pour
`npm test -- --watch=false --browsers=ChromeHeadless`).

### Toujours appeler depuis la racine du workspace, avec `--cwd`

Les playbooks font `cd {repo-path}` avant de builder — et là, le chemin relatif
`Tools/timing/measure.sh` ne résout plus. D'où **`--cwd {repo-path}`** : le
wrapper entre lui-même dans le repo, l'appel reste à la racine, il n'y a qu'une
seule forme d'invocation à retenir.

```bash
# ✔ depuis la racine
Tools/timing/measure.sh --task task-183 --step develop --repo client-mobile \
    --cwd Client/Mobile --kind test -- npm test -- --watch=false --browsers=ChromeHeadless

# ✘ après un `cd Api/Mail` : le chemin du wrapper est faux
cd Api/Mail && Tools/timing/measure.sh ... -- dotnet build ...
```

`--cwd` est résolu d'abord relativement au répertoire courant, puis à la racine
de la forge : il fonctionne donc aussi si l'agent a déjà changé de répertoire.
Un `--cwd` introuvable sort en **66 sans exécuter la commande** — jamais une
mesure silencieusement fausse. Le répertoire est enregistré dans le journal.

`git push` reste l'exception : le hook `verify-before-push.sh` exige d'être
**dans** le repo, et ce n'est de toute façon pas une commande mesurée.

### Le vocabulaire `--kind`

C'est la dimension qui répond à « combien de cycles coûte une task ». Un seul
mot par nature de commande, sinon les agrégats ne veulent plus rien dire :

| `--kind` | À utiliser pour |
|---|---|
| `build` | `dotnet build`, `npm run build`, `nx affected -t build` |
| `test` | `dotnet test`, `npm test`, `nx affected -t test` (ajouter `--label coverage` quand la passe est instrumentée OpenCover) |
| `scan` | `dotnet sonarscanner begin` / `end`, attente de traitement serveur |
| `lint` | `nx affected -t lint`, `ng lint` |
| `capture` | Playwright / `/verify-visual` |
| `restore` | `dotnet restore`, `npm ci` |
| `nuget-wait` | `gh run watch` sur la CI de publication DTO/interop (temps mort série) |

`--repo` prend une clé de la table des repos de `CLAUDE.md` (`api-mail`,
`client-blazor`, `client-angular`, `client-mobile`, `dtos-mss`, …).

## Protocole (obligatoire pour chaque étape de la chaîne)

1. `step.sh start` en entrée d'étape, **avant** le pré-flight.
2. `measure.sh` autour de **chaque** commande coûteuse (build, test, scan, lint,
   capture, restore, attente CI). Les commandes git, les lectures de fichier et
   les appels d'API ne sont pas mesurés : ils sont dans le bruit.
3. `step.sh end` en sortie — **y compris quand l'étape skip ou échoue** :
   - skip propre → `--status skipped --note "api-mail untouched"`
   - fail-fast → `--status failed --note "cap 5 itérations"`
   - boucle best-effort → `--iterations N`

   Une étape qui skippe sans le mesurer crée un trou dans le journal : on ne
   peut plus distinguer « gratuit » de « pas mesuré ».
4. `step.sh end` rafraîchit automatiquement la section `## Timings` du task file
   (via `report.sh --sync`), donc **aucune table n'est à rédiger à la main** —
   et surtout, aucune durée n'est à estimer par l'agent.

### Run id (regroupement par run `/forge`)

Les variables d'environnement ne survivent pas d'un appel Bash à l'autre, donc
le run id vit dans un fichier :

```bash
# au début d'un run /forge
mkdir -p metrics/.state && echo "forge-20260831-183-190" > metrics/.state/run_id
# à la fin
rm -f metrics/.state/run_id
```

Un `/develop` lancé seul, hors run, enregistre `run_id: "-"` — c'est normal.

## Lire le tableau qui compte

```bash
Tools/timing/report.sh --by-kind
```

Il donne, par étape et par nature de commande : le nombre d'occurrences, le
**nombre par task**, le total, la médiane et le max. C'est la mesure qui
valide ou invalide chaque levier d'optimisation :

- « le hook pre-push rebuild ce que l'étape vient de valider » → `build` par
  task doit baisser après le marqueur green ;
- « Sonar Phase 2 n'a rien à faire dans le chemin critique » → comparer le
  `--by-kind --step sonar` avant / après ;
- « paralléliser les 3 lanes » → le total des durées d'étapes ne bouge pas, mais
  le temps mur du cycle baisse : c'est la seule optimisation où `Total cycle`
  et la somme des étapes divergent (et le playbook doit le dire).

Comparer deux périodes : `--since 2026-09-01` sur les deux moitiés du journal.

## Limites assumées

- **Le temps mur d'un cycle n'est pas la somme des étapes** : la somme ignore
  ce qui se passe entre deux étapes (raisonnement de l'agent, allers-retours
  d'outils). L'écart est justement l'overhead de la boucle agentique — utile à
  connaître, mais ne pas le confondre avec du temps de build.
- **Chaque appel `measure.sh` ajoute ~0,2 s** (démarrage de bash + hook
  PreToolUse). Négligeable devant un build .NET, à ne pas utiliser pour
  chronométrer des commandes triviales.
- **Écrivain unique.** Le journal suppose un seul run à la fois (c'est la règle
  actuelle de `/forge`). Le jour où des lanes parallèles écrivent en même temps,
  des lignes peuvent s'entrelacer — le format une-ligne-un-événement limite les
  dégâts à un ordre non garanti, jamais à une ligne corrompue.
- `report.sh` est le seul composant qui dépend de python. Le chemin chaud
  (`measure.sh`, `step.sh`) est en bash pur : un interpréteur manquant ne peut
  jamais casser un build, seulement le rapport.
