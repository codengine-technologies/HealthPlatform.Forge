# agents/sonar.md — Sonar cleanup agent

## Role

You automate SonarQube issue resolution on `api-mail`. Since the **autonomous
forge inversion of 2026-04-27**, you are no longer a "philosophical exception"
to a no-code rule — you are a **standard step of the autonomous cycle**, sitting
between `/forge-simplify` (the `/simplify` quality pass, itself chained from
`/develop`) and `/review` (which opens the PR).

You run end-to-end : analysis → fetch issues → implement fixes (with tests
first when behaviour changes) → commit → push → re-analyse → iterate. At the
end you hand over to `/review` which opens the PR for human merge (HAG rule 10
still applies — the human merges, never the forge).

## Zero-new-debt principle (non-négociable)

**Aucune nouvelle dette ne doit être introduite par une PR passant par `/sonar`.**
Cela impose un découpage en deux phases au sein du même run :

### Phase 1 — New code (MANDATORY, exhaustive, bloquante)

Cible : 100% des findings du **new code period** (au sens SonarQube — code
ajouté/modifié depuis la baseline du Quality Gate, typiquement le merge-base
avec `develop`).

- **Tous** les bugs, vulnérabilités, code smells du new code → **doivent être
  fixés**. Pas d'acceptation, pas de cap d'itérations.
- **Tous** les security hotspots du new code → doivent être traités (fix si
  applicable, sinon marqués `SAFE` / `ACKNOWLEDGED` avec justification dans
  le journal). Aucun ne peut rester `TO_REVIEW`.
- **Couverture du new code** (`new_coverage`) → doit atteindre la cible
  (`coverage` de `agents/sonar-targets.yml`, par défaut **95%**). Si elle
  n'est pas atteinte, l'agent **doit créer les tests unitaires manquants**
  jusqu'à atteindre la cible. Pas d'acceptation.
- **Quality Gate sur le new code** → doit passer (`OK`). Sinon, on continue
  Phase 1.
- **Règles blacklistées** : la blacklist (`agents/sonar-blacklist.yml`)
  **NE s'applique PAS au new code**. Si une règle blacklistée déclenche sur
  du new code, deux options seulement :
  1. fix manuel (préféré),
  2. halt via `questions/{task-id}.md` si le fix dépasse le périmètre de la
     task.
  Jamais de skip silencieux sur du new code.
- **Aucun cap d'itérations** sur Phase 1. La phase tourne jusqu'à new-code
  Quality Gate vert OU jusqu'à blocage (auquel cas → `questions/` et halt,
  pas d'acceptation).
- **Conditions d'arrêt en échec** (Phase 1 bloquée → `questions/` + halt,
  PAS de hand-off vers `/review`) :
  - Une issue new-code non résolvable sans dépasser le périmètre de la task
  - Couverture new-code impossible à atteindre (code non testable sans
    refactor structurel hors scope)
  - Build / tests cassés par un fix qui ne peut être rollback
  - 2 itérations consécutives sans progression sur le new code

### Phase 2 — Legacy debt (best-effort, optionnelle)

Cible : la dette préexistante (issues hors new code period). Ne démarre
**qu'après** Phase 1 verte. Conserve le modèle historique : 5 itérations max,
blacklist appliquée, acceptation des issues restantes, hand-off à `/review`
quoi qu'il arrive.

Cette phase peut être entièrement skipped si le temps manque ou si la
baseline est déjà bonne — elle ne bloque jamais le cycle autonome.

## Autonomous cycle position

```
/develop {task-id}   →   /forge-simplify {task-id}   →   /sonar {task-id}   →   /lint-angular {task-id}   →   /lint-mobile {task-id}   →   /verify-visual {task-id}   →   /review {task-id}   →   /tech-writer
                                                          ↑
                                                          you are here
```

`/lint-angular` is the Angular counterpart of `/sonar` (best-effort
ESLint cleanup on `Client/Angular/front/`). It is skipped cleanly when
the task didn't touch `client-angular` ; in that case `/sonar` hands off
to `/review` directly. See `agents/lint-angular.md`.

Two important properties of the cycle :

- **Same branch as `/develop`.** `/sonar` reuses the feature branch
  `feat/{task-id}-{slug}` already pushed by `/develop`. It does NOT create
  a chore branch (the historical "stand-alone Sonar run" mode kept its own
  `chore/sonar-api-mail-{YYYYMMDD}` branch, but in the autonomous chain that
  branch model is replaced by per-task chaining — see "Two invocation modes"
  below).

- **Best-effort on legacy debt only.** 5 iterations max for Phase 2. After
  that, accept the remaining **legacy** issues and hand off to `/review`.
  Phase 1 (new code) is **never** best-effort — see the zero-new-debt
  principle above. The autonomous cycle prioritises forward progress over
  a perfect Sonar Quality Gate **on legacy code**, jamais sur le new code.

## Two invocation modes

`/sonar` supports two distinct invocation modes — the playbook below is shared
between them but the pre-flight, branch model and hand-off differ.

### Mode A — chained from `/forge-simplify` (autonomous cycle, default)

- Triggered by `/forge-simplify {task-id}` once the feature implementation is
  committed, pushed, and the `/simplify` quality pass has run
- Task file : the existing `tasks/wip-{task-id}.md` (no new file)
- Branch : the existing `feat/{task-id}-{slug}` on `api-mail` (reused)
- Iterations : best-effort 5 max, accept remaining issues
- Hand-off : `/review {task-id}` (the same task, NOT a separate Sonar PR)
- Skip cleanly when the task did not touch `api-mail`

### Mode B — stand-alone (manual housekeeping)

- Triggered by the human via `/sonar api-mail` with no task in flight
- Task file : `tasks/todo-sonar-api-mail-{YYYYMMDD}.md` (created by this
  command via `/start`)
- Branch : `chore/sonar-api-mail-{YYYYMMDD}` on `api-mail` only
- Iterations : up to 5, with progression-based early-stop
- Hand-off : `/review sonar-api-mail-{YYYYMMDD}` opens a dedicated Sonar PR
- Same-day re-run is refused (duplicate branch / task detection)

In both modes : repo `api-mail` only (path `Api/Mail/`, solution
`HealthPlatform.Api.Mail.sln`), token from `$SONAR_TOKEN`, blacklist from
`agents/sonar-blacklist.yml`, S3776 excluded (handled by `/sonar-s3776`).

## Hard targets (from `agents/sonar-targets.yml`)

Long-term project-wide targets :

- `bugs = 0`
- `vulnerabilities = 0`
- `sqale_rating = A` (maintainability)
- `coverage >= 95%`

A single `/sonar` run is NOT expected to reach these on the **whole project**
; Phase 2 (legacy) is expected to make significant progress.

**On the new code period, however, these targets are non-negotiable per
run** (zero-new-debt principle) :

- `new_bugs = 0`
- `new_vulnerabilities = 0`
- `new_security_hotspots_reviewed = 100%`
- `new_code_smells = 0` (toutes sévérités, sauf règles blacklistées —
  voir ci-dessus, la blacklist ne couvre PAS le new code)
- `new_coverage >= 95%` (ou la valeur courante de `coverage` dans
  `sonar-targets.yml`)
- Quality Gate sur le new code = `OK`

Early-stop if all project-wide targets AND the new-code Quality Gate are
already met.

## Environment

Read the SonarQube endpoint and token from environment variables. NEVER hardcode
the token in the repo. Expected vars :

- `SONAR_HOST_URL` (e.g. `http://localhost:9001`)
- `SONAR_TOKEN` (e.g. `squ_xxxxxxxxxxxxxxxx`)
- `SONAR_PROJECT_KEY` (e.g. `healthplatform`)

### Loading order (Step 0 reads these in order)

1. The bash session env (if `$SONAR_TOKEN` is already exported, use it).
2. The workspace-level `.env` file at `D:\TechWatch\HealthPlatform\.env`.
   The forge `.gitignore` excludes it by default — safe to commit credentials
   there.
3. The api-mail `.env` at `Api/Mail/.env` (also gitignored).

If a value is found in (2) or (3) but not yet exported, source the file with
`set -a; source <path>; set +a` so the values propagate to child processes
(e.g. `dotnet sonarscanner`).

If after all three steps any of the three vars is still missing → abort with
a clear message naming the missing variable(s) and pointing the human at
`D:\TechWatch\HealthPlatform\.env` as the recommended location (workspace-wide,
gitignored).

---

## Steps

### Step 0 — Pre-flight

0. **Load Sonar env vars at the head of every Bash call.** Claude Code's
   Bash tool spawns a fresh shell per invocation — env vars set in one
   call do NOT persist to the next. So every `/sonar` Bash command MUST
   start with the same one-liner :

   ```bash
   set -a; [ -f /d/TechWatch/HealthPlatform/.env ] && source /d/TechWatch/HealthPlatform/.env; set +a
   ```

   That sources the workspace-level `.env` (auto-gitignored — see the
   workspace `.gitignore` rule "ignore everything by default"). Append the
   actual Sonar/curl/docker command after the snippet, separated by `;` or
   `&&`. Do NOT split the env load and the command into two Bash calls —
   the second call won't see the env vars.

   After sourcing, if any of `SONAR_HOST_URL`, `SONAR_TOKEN`,
   `SONAR_PROJECT_KEY` is missing → abort and tell the human to add the
   missing var to `D:\TechWatch\HealthPlatform\.env`.

0a. **Start the SonarQube Docker container if it is down.** SonarQube runs in
    Docker Desktop on this workstation as a long-lived (stopped) container.
    The agent is responsible for starting it — do NOT ask the human, do NOT
    skip the run.

    ```bash
    # Probe the server first
    if ! curl -sf --max-time 3 "$SONAR_HOST_URL/api/system/status" >/dev/null 2>&1; then
      # Find the container by image (sonarqube:* or *sonar*) and start it.
      cid=$(docker ps -a --filter "ancestor=sonarqube" --format '{{.ID}}' | head -1)
      if [ -z "$cid" ]; then
        cid=$(docker ps -a --format '{{.ID}}\t{{.Names}}\t{{.Image}}' \
              | awk 'tolower($0) ~ /sonar/ { print $1; exit }')
      fi
      if [ -z "$cid" ]; then
        # Abort — no container exists. Ask the human to create one.
        echo "/sonar refused — no SonarQube container in Docker Desktop." >&2
        echo "Create one with:  docker run -d --name sonarqube -p 9001:9000 sonarqube:lts-community" >&2
        exit 1
      fi
      docker start "$cid"

      # Poll until status=UP (max 90 s — Sonar boot is ~30-60 s on cold start)
      for i in $(seq 1 30); do
        status=$(curl -sf --max-time 3 "$SONAR_HOST_URL/api/system/status" \
                 | grep -oE '"status":"[A-Z]+"' | cut -d'"' -f4)
        if [ "$status" = "UP" ]; then
          break
        fi
        sleep 3
      done

      if [ "$status" != "UP" ]; then
        echo "/sonar refused — SonarQube did not reach status=UP within 90 s." >&2
        echo "Container started but server not ready. Check 'docker logs $cid'." >&2
        exit 1
      fi
    fi
    ```

    Implementation notes :
    - The container name is **not** hardcoded. The agent discovers it by
      image (`sonarqube:*`) first, then falls back to a name/image pattern
      match (`*sonar*`).
    - Polling cap : 90 s. Cold boot from a stopped state is normally
      30-60 s ; if longer, surface the failure rather than block the chain.
    - The agent never `docker run`s a fresh container — that would drop the
      project state and invalidate `$SONAR_TOKEN`. Only `docker start` on
      an existing one. If none exists, abort with the suggested create command.

1. **Detect the mode** from the invocation argument :
   - `/sonar api-mail` (or `/sonar` with no task in flight) → **Mode B**
     (stand-alone)
   - `/sonar {task-id}` where `tasks/wip-{task-id}.md` exists → **Mode A**
     (chained)

2. **Mode A — chained** : verify `api-mail` is on the existing feature
   branch with a clean tree :
   ```bash
   cd Api/Mail
   git symbolic-ref --short HEAD    # must equal feat/{task-id}-{slug}
   git status --porcelain            # must be empty (build/test artefacts only)
   ```
   If the task didn't touch `api-mail` (no commits since the merge-base with
   `develop`), **skip cleanly** : log "no api-mail change → /sonar skipped"
   and chain directly to `/review`.

3. **Mode B — stand-alone** : verify `api-mail` is on `develop` with a clean
   working tree :
   ```bash
   cd Api/Mail
   git symbolic-ref --short HEAD    # must be "develop"
   git status --porcelain            # must be empty
   ```
   Any deviation → abort with the reason. The human cleans up and retries.

2. Verify SonarQube is reachable :
   ```bash
   curl -sf "$SONAR_HOST_URL/api/system/status"
   ```
   Expect `"status":"UP"`. Otherwise abort.

3. Verify `dotnet-sonarscanner` is installed :
   ```bash
   dotnet tool list -g | grep dotnet-sonarscanner
   ```
   Otherwise install it : `dotnet tool install --global dotnet-sonarscanner`.

4. **Mode B only — refuse same-day re-run.** Compute `YYYYMMDD` from today's
   date and abort if any of the following already exists for this date :
   - a task file `tasks/{todo|wip|review|done}-sonar-api-mail-{YYYYMMDD}.md`
   - a local branch `chore/sonar-api-mail-{YYYYMMDD}` (`git branch --list`)
   - a remote branch `origin/chore/sonar-api-mail-{YYYYMMDD}`
     (`git ls-remote --heads origin`)

   If any is found → abort with a clear message :
   ```
   /sonar refusé — un run existe déjà pour {YYYYMMDD} :
     - tasks/wip-sonar-api-mail-20260420.md
     - chore/sonar-api-mail-20260420 (local + origin)
   Finalise (/review) ou nettoie le run en cours, puis relance demain.
   ```
   The forge does not auto-delete anything — the human decides.

   This refusal does NOT apply to Mode A — the chained invocation reuses the
   feature task's branch, so multiple `/sonar` runs in a single day are
   normal (one per task).

5. Fetch **baseline KPIs** (before any work) via `/api/measures/component` and
   remember them. They will be the "baseline" column of the final PR body.

### Step 1 — Early-stop if targets already met

If baseline already satisfies all hard targets (`bugs=0`, `vulnerabilities=0`,
`sqale_rating=A`, `coverage>=95`) **AND** the new-code Quality Gate is `OK`
(no new-code issues, `new_coverage>=95`), print a congratulations message
and stop. Nothing to do.

Otherwise, decide which phases to run :
- If new-code Quality Gate is RED OR any `new_*` finding exists OR
  `new_coverage < target` → **Phase 1 mandatory**.
- If project-wide targets are not met after Phase 1 → **Phase 2 best-effort**.

### Step 2 — Create task + branch (Mode B only)

**Mode A — chained** : skip this step entirely. The branch and task already
exist (created by `/develop`). Jump directly to Step 3 with the existing
`feat/{task-id}-{slug}` branch.

**Mode B — stand-alone** :

1. Compute `YYYYMMDD` from today's date (the workspace is on Windows ; use
   `date +%Y%m%d` in bash).
2. Create `tasks/todo-sonar-api-mail-{YYYYMMDD}.md` using the template below.
3. Invoke `/start sonar-api-mail-{YYYYMMDD} no-code` (the `no-code` flag is
   mandatory here — Sonar runs `/sonar` itself, not `/develop`, so we don't
   want `/start` to chain into `/develop`). `/start` creates the branch
   `chore/sonar-api-mail-{YYYYMMDD}` on `api-mail` and renames the task
   to `wip-*`.

   Note : `/start`'s pre-flight will check every repo in the polyrepo is on
   `develop`. If another repo is on a feature branch, `/start` aborts. That is
   the normal forge behaviour ; `/sonar` does not bypass it. The human resolves
   and retries.

**Task template** :

```markdown
# todo-sonar-api-mail-{YYYYMMDD}.md — Sonar cleanup api-mail {YYYY-MM-DD}

**Repos**: api-mail
**Dependencies**: aucune
**Type**: chore (→ /start MUST use `chore/` branch prefix)

## Objectif

Nettoyage Sonar automatisé sur `api-mail`. Traitement des bugs, vulnérabilités,
hotspots de sécurité, et code smells par lots catégorie→règle plafonnés à
30 fichiers par itération. Chaque fix est couvert par un test unitaire (écrit
en amont si le fix change le comportement, sinon validé par les tests
existants). Max 5 itérations sur la même branche.

## Baseline (snapshot avant run)

| Métrique            | Baseline |
|---------------------|----------|
| Bugs                | {N}      |
| Vulnerabilities     | {N}      |
| Security Hotspots   | {N}      |
| Code Smells         | {N}      |
| Coverage            | {X}%     |
| Duplication         | {X}%     |
| Reliability rating  | {A-E}    |
| Security rating     | {A-E}    |
| Maintainability     | {A-E}    |

## Cibles long terme

- Bugs = 0
- Vulnerabilities = 0
- Maintainability rating = A
- Coverage >= 95%

## Definition of Done

- [ ] Build passes on `api-mail` (0 errors, Release config)
- [ ] Tests pass on `api-mail` (0 failures)
- [ ] Progression significative vs baseline : >=10% de réduction des issues
      OU baisse d'au moins un rating (Reliability / Security / Maintainability)
- [ ] Aucun fix comportemental sans test unitaire ajouté en amont
- [ ] Aucune règle blacklistée (voir `agents/sonar-blacklist.yml`) traitée
- [ ] Journal d'itération rempli (voir section `## Journal` ci-dessous)
- [ ] Aucune régression (tous les tests préexistants restent verts)

## Manual Test Plan

1. `cd Api/Mail`
2. `dotnet build HealthPlatform.Api.Mail.sln --configuration Release`
3. `dotnet test HealthPlatform.Api.Mail.sln --configuration Release`
4. Lancer l'API locale (Aspire AppHost) et fumer un flux minimal :
   envoi d'un mail MSS, vérification des logs, accès à un endpoint read.
5. Vérifier sur SonarQube : http://localhost:9001/dashboard?id=healthplatform-api-mail
   que le Quality Gate n'a pas régressé.

## Journal

(rempli par l'agent au fur et à mesure des itérations)

| Iter | Catégorie | Règles traitées | Fichiers | Issues fixed | Issues skipped | Build | Tests | KPIs après |
|------|-----------|-----------------|----------|--------------|----------------|-------|-------|------------|
| 1    | ...       | ...             | ...      | ...          | ...            | ✓     | ✓     | ...        |
```

### Step 3 — Phase 1 loop : new code (MANDATORY, no iteration cap)

Cette boucle ne s'arrête que sur l'un des deux états terminaux :
- **Succès** : new-code Quality Gate = `OK`, `new_coverage >= target`,
  zéro `new_bugs / new_vulnerabilities / new_code_smells`, 100% des
  `new_security_hotspots` revus.
- **Blocage** : voir "Conditions d'arrêt en échec" du Zero-new-debt
  principle → écrire `questions/{task-id}.md` et **halt** (pas de hand-off
  vers `/review`).

Pour chaque itération de Phase 1 :

#### 3.1 Fetch new-code issues

**Filtre `inNewCodePeriod=true` obligatoire** :

```bash
curl -s -u "$SONAR_TOKEN:" \
  "$SONAR_HOST_URL/api/issues/search?componentKeys=$SONAR_PROJECT_KEY&resolved=false&inNewCodePeriod=true&ps=500&s=SEVERITY&asc=false" \
  > /tmp/sonar-newcode-issues-iter{iter}.json
```

For security hotspots :

```bash
curl -s -u "$SONAR_TOKEN:" \
  "$SONAR_HOST_URL/api/hotspots/search?projectKey=$SONAR_PROJECT_KEY&status=TO_REVIEW&inNewCodePeriod=true&ps=500" \
  > /tmp/sonar-newcode-hotspots-iter{iter}.json
```

Fetch the new-code coverage :

```bash
curl -s -u "$SONAR_TOKEN:" \
  "$SONAR_HOST_URL/api/measures/component?component=$SONAR_PROJECT_KEY&metricKeys=new_coverage,new_line_coverage,new_branch_coverage,new_uncovered_lines,new_uncovered_conditions"
```

#### 3.2 Build the batch — NO blacklist, NO file cap

- **La blacklist NE s'applique PAS** au new code (zero-new-debt principle).
- Pas de cap à 30 fichiers — on doit traiter **tout** le new code. Garder
  un cap de 100 issues par itération uniquement pour cadencer les commits ;
  les itérations suivantes traitent le reste.
- Tri identique à l'ancien (bugs > vuln > hotspots > smells, par sévérité).

#### 3.3 Apply fixes — test-first quand comportemental

Même classification que l'ancienne section 3.4/3.5 (refactor pur vs
comportemental, RED-GREEN pour le comportemental).

Spécificité Phase 1 : si une issue est blacklistée ET sur du new code,
deux options seulement :
1. fix manuel (privilégié),
2. halt via `questions/{task-id}.md`.

Jamais de skip silencieux.

#### 3.4 Combler les trous de couverture du new code

Après avoir fixé les issues, calculer les lignes/branches non couvertes du
new code :

```bash
curl -s -u "$SONAR_TOKEN:" \
  "$SONAR_HOST_URL/api/measures/component_tree?component=$SONAR_PROJECT_KEY&metricKeys=new_uncovered_lines,new_uncovered_conditions&qualifiers=FIL&ps=500&s=metric&metricSort=new_uncovered_lines&asc=false&inNewCodePeriod=true"
```

Pour chaque fichier ayant `new_uncovered_lines > 0` ou
`new_uncovered_conditions > 0` :

1. Lire le fichier source et la couverture détaillée (rapport OpenCover dans
   `TestResults/`).
2. Identifier les méthodes / branches non couvertes parmi les lignes du new
   code (intersection avec le diff `git diff origin/develop...HEAD --name-only`
   et `git blame` si nécessaire).
3. **Écrire les tests unitaires manquants** dans le projet de tests
   correspondant (mirror `tests/mss.mail.{layer}.tests/`). Arrange / Act /
   Assert, NSubstitute pour les mocks, un comportement par test.
4. Exécuter le test → vérifier qu'il passe et qu'il couvre effectivement
   les lignes/branches ciblées.

Itérer jusqu'à `new_coverage >= target`. Si une portion du code est
intrinsèquement non testable sans refactor structurel hors scope → halt via
`questions/`.

#### 3.5 Build + full test suite

Identique à l'ancienne 3.6 (build + tests, rollback du batch si KO).

#### 3.6 Commit + push

Identique à l'ancienne 3.7. Préfixer les commits Phase 1 :

```
fix(sonar/new): resolve N occurrences of {ruleKey} — {ruleName}
test(sonar/new): cover {file/feature} (new-code coverage)
```

#### 3.7 Re-analyse et vérification

Re-lancer l'analyse Sonar complète (commands de la section "Sonar analysis
commands"), attendre la fin du traitement serveur, puis fetch :

```bash
curl -s -u "$SONAR_TOKEN:" \
  "$SONAR_HOST_URL/api/qualitygates/project_status?projectKey=$SONAR_PROJECT_KEY"
```

Lire `projectStatus.conditions[]` et vérifier les conditions sur new code
(`new_*` metrics) :
- Toutes les conditions new-code en `OK` → **sortir de Phase 1**, passer
  Phase 2.
- Au moins une condition new-code en `ERROR` → itération suivante de
  Phase 1.
- 2 itérations consécutives sans amélioration sur le new code → halt via
  `questions/`.

### Step 4 — Phase 2 loop : legacy debt (best-effort, max 5 iterations)

Ne démarre que si Phase 1 est verte. Boucle historique conservée :

For `iter = 1..5` :

#### 4.1 Fetch issues

Identique à l'ancienne 3.1 (sans `inNewCodePeriod`), mais ajouter le filtre
pour **exclure** le new code (déjà traité en Phase 1) :

```bash
curl -s -u "$SONAR_TOKEN:" \
  "$SONAR_HOST_URL/api/issues/search?componentKeys=$SONAR_PROJECT_KEY&resolved=false&inNewCodePeriod=false&ps=500&s=SEVERITY&asc=false" \
  > /tmp/sonar-legacy-issues-iter{iter}.json
```

#### 4.2 Filter + sort (legacy only)

1. **La blacklist S'APPLIQUE** ici (Phase 2 = legacy). Drop any issue whose
   `rule` matches a blacklisted key. Log them as "skipped (blacklisted)".
2. **Sort by priority** :
   1. Bugs with severity BLOCKER, then CRITICAL, then MAJOR, then MINOR
   2. Vulnerabilities with severity BLOCKER, then CRITICAL, then MAJOR, then MINOR
   3. Security hotspots with priority HIGH, then MEDIUM, then LOW
   4. Code smells with severity CRITICAL, then MAJOR, then MINOR, then INFO

#### 4.3 Build the iteration's batch — **Strategy C**

Within the top-priority category still having issues, pick all issues of the
**most common rule** (or the top 2-3 rules if the top rule has few issues)
until you hit the cap :

- **Max 30 distinct files touched per iteration**
- **Max 100 issues per iteration** (absolute cap, to keep iterations bounded)

If all issues of the chosen category are blacklisted or capped out, advance
to the next category in the same iteration.

#### 4.4 Classify each issue — behavioural vs pure refactor

For each issue in the batch, read the `file:line`, the rule message, and
enough context to classify :

- **Pure refactor** — no behaviour change (e.g. rename unused var, replace
  `.ToList().Count` with `.Count()`, collapse `if/else if` chains, remove
  unreachable code, optimise LINQ, switch to `is null`, merge using statements,
  etc.). Existing tests are the safety net.

- **Behavioural** — the fix changes runtime behaviour (e.g. add a null check
  that changes a flow, fix a swapped argument, fix a wrong cast, add missing
  `ConfigureAwait`, plug a disposable leak that alters timing). **A unit test
  MUST exist or be added before the fix.**

If the classification is ambiguous → treat as **behavioural** (safer).

#### 4.5 Apply fixes — test-first for behavioural

For each **behavioural** issue :

1. Find or create the appropriate test file (mirror the source structure under
   `tests/mss.mail.{layer}.tests/`).
2. Write a unit test that captures the **current buggy behaviour reproduced**
   and asserts the **expected behaviour after fix**. Run it → must be RED.
3. Apply the fix.
4. Re-run the specific test → must be GREEN.

For each **pure refactor** issue :

1. Apply the fix.
2. Run the project's tests (`dotnet test`) → must stay GREEN.
3. If any test turns RED → the "pure refactor" classification was wrong.
   Rollback the fix, reclassify as behavioural, go through step-first test
   path.

#### 4.6 Build + full test suite

After the whole batch is applied :

```bash
cd Api/Mail
dotnet build HealthPlatform.Api.Mail.sln --configuration Release --verbosity quiet
dotnet test  HealthPlatform.Api.Mail.sln --configuration Release --logger "console;verbosity=minimal"
```

- Build KO → rollback the whole batch (`git reset --hard HEAD` before any
  commit). Log the failure, try a smaller batch (halve the size) and retry
  once. If it still fails → stop the loop, go to Step 5 with what's already
  committed.
- Tests KO → same rollback logic.

#### 4.7 Commit + push

Group commits by rule for diff readability. Message per commit :

```
fix(sonar): resolve N occurrences of {ruleKey} — {ruleName}
```

For multiple rules in the same iteration, one commit per rule. Example :

```
fix(sonar): resolve 12 occurrences of S1481 — unused local variable
fix(sonar): resolve 5 occurrences of S2589 — boolean literal on both branches
test(sonar): add unit tests for null-guard fixes (S2259)
fix(sonar): resolve 3 occurrences of S2259 — null reference
```

Then :

```bash
git push origin chore/sonar-api-mail-{YYYYMMDD}
```

#### 4.8 Re-analyse

Run the full Sonar analysis (begin → build → test with coverage → end) using
the same commands documented in this file's "Sonar analysis commands" section
below. Wait for the server to process the report (poll
`/api/ce/component?component=$SONAR_PROJECT_KEY` until `queue` is empty and
`current.status=SUCCESS`, with a 60s timeout).

Fetch the new KPIs. Append a row to the task's `## Journal` table.

#### 4.9 Evaluate progression

Compute :

- `issueDeltaPct = (issuesBefore - issuesAfter) / issuesBefore * 100`
- `ratingImproved = any of reliability_rating / security_rating / sqale_rating
   improved by at least one step compared to baseline OR previous iteration`

**Continue** if `issueDeltaPct >= 10` OR `ratingImproved` is true, AND
`iter < 5`, AND at least one non-blacklisted issue remains.

**Stop** otherwise (no significant progression, or max iter reached, or
nothing left to fix).

**Best-effort acceptance** (since the autonomous inversion of 2026-04-27) :
when the loop stops because of the iteration cap (`iter == 5`) but issues
remain, **do not halt the cycle**. Log "Sonar best-effort (legacy) : N
issues remaining after 5 iterations — accepted, handed off to /review" in
the task's `## Journal` table. The autonomous chain prioritises forward
progress over Sonar perfection **on legacy code only**.

**Cette acceptance ne s'applique JAMAIS à Phase 1 (new code).** Si Phase 1
est bloquée, l'agent halt via `questions/` et n'invoque PAS `/review` —
zero-new-debt principle.

The cycle only halts (via `questions/{task-id}.md`) on **tooling failure**
— SonarQube unreachable mid-run, scanner crash, build/test broken by a
faulty fix that can't be rolled back, GitHub API failure on push **— OR
on Phase 1 blockage**.

### Step 5 — Handover to /lint-angular → /lint-mobile (or /review)

**Pré-condition impérative** : Phase 1 doit être verte (new-code Quality
Gate `OK`, `new_coverage >= target`, zéro `new_*` finding non traité).
Sinon, NE PAS appeler `/lint-angular`, `/lint-mobile` ni `/review` — écrire
`questions/{task-id}.md` et halt.

**Mode A — chained** :

1. Append a Sonar summary to the existing task's `## Develop log` section
   (or create `## Sonar log` if missing). **Le tableau de KPIs
   baseline → final est OBLIGATOIRE** — c'est lui que `/review` recopie
   dans le body de la PR et dans son rapport de fin de cycle (le monitoring
   qualité fait partie du flux, pas d'un dashboard externe) :
   ```markdown
   ## Sonar log
   - Phase 1 (new code) : ✓ Quality Gate OK, new_coverage = {X}%
   - Phase 1 — Issues fixées : {count} (bugs / vuln / smells / hotspots)
   - Phase 1 — Tests ajoutés : {count}
   - Phase 2 (legacy) : itérations {N} / 5
   - Phase 2 — Issues fixées : {count}
   - Phase 2 — Issues restantes : {count} (best-effort acceptance)
   - Build / tests : ✓ green

   ### KPIs qualité (baseline → final)

   | Métrique | Baseline | Final | Δ |
   |---|---|---|---|
   | Quality Gate (new code) | {OK/ERROR} | {OK/ERROR} | {→} |
   | New coverage | {X}% | {X}% | {±X pt} |
   | Bugs | {N} | {N} | {±N} |
   | Vulnerabilities | {N} | {N} | {±N} |
   | Security hotspots | {N} | {N} | {±N} |
   | Code smells | {N} | {N} | {±N} |
   | Coverage (projet) | {X}% | {X}% | {±X pt} |
   | Duplication | {X}% | {X}% | {±X pt} |
   | Reliability / Security / Maintainability | {A-E}/{A-E}/{A-E} | {A-E}/{A-E}/{A-E} | {→} |
   ```
   Les valeurs viennent des fetchs déjà effectués : baseline du Step 0.5,
   final de la dernière re-analyse (Step 3.7 / 4.8). Aucune mesure
   supplémentaire n'est requise — c'est de la restitution, pas un re-scan.
2. **Feed `conventions/csharp.md`** (workspace root) — the self-improving
   loop. For each Sonar rule fixed **manually** in this run on code written
   by `/develop` (Phase 1 new-code findings in priority ; Phase 2 legacy
   fixes count only when the rule is likely to recur in fresh code) :
   - entry exists for the rule → increment **Occurrences**, append the
     task-id to **Origine** ;
   - no entry → create one (format documented at the top of the file),
     `Occurrences : 1`.
   The goal : `/develop` reads that file before coding, so the same rule
   never triggers on new code twice. Skip when the run had nothing to fix.
3. **Do not rename the task.** The task stays in `wip-*` — `/review` is
   responsible for the `wip → review → done` transitions.
4. **Decide the next step** along the fixed pipeline `/lint-angular →
   /lint-mobile → /review` (each self-skips when its repo is untouched) :
   - Task lists `client-angular` in `**Repos**:` **OR**
     `git -C Client/Angular/front status --porcelain` is non-empty
     (uncommitted Angular work left by `/develop`) → invoke
     `/lint-angular {task-id}`. That step hands off to `/lint-mobile`,
     then `/review`.
   - Else, task touched `client-mobile` (lists it in `**Repos**:` **OR**
     `git -C Client/Mobile diff --name-only origin/develop...HEAD` is
     non-empty) → invoke `/lint-mobile {task-id}` directly. It hands off
     to `/review`.
   - Otherwise → invoke `/review {task-id}` directly (no frontend lint
     work to do).

**Mode B — stand-alone** :

1. Update the task's DOD checkboxes based on what was actually achieved.
2. Fill the final KPI table in the PR body template (baseline vs final).
3. Rename the task to `review-sonar-api-mail-{YYYYMMDD}.md`.
4. Invoke `/review sonar-api-mail-{YYYYMMDD}`. A stand-alone Sonar run
   never touches `client-angular`, so `/lint-angular` is not in the
   hand-off path for Mode B.

In every chain path, `/review` runs autonomously (no human approval prompt
— see the autonomous-mode `/review` spec) : rebuild + retest, DOD
verification, code review, commit + push + sync develop, open PR with
label `awaiting-human-merge`, rename `done-*`, then chain `/tech-writer`.
The human merges manually (HAG rule 10).

---

## Sonar analysis commands (used in Step 0, Step 3.7, Step 4.8)

### Cleanup
```bash
cd Api/Mail
rm -rf TestResults
mkdir -p TestResults
```

### Begin
```bash
dotnet sonarscanner begin \
  /k:"$SONAR_PROJECT_KEY" \
  /d:sonar.host.url="$SONAR_HOST_URL" \
  /d:sonar.token="$SONAR_TOKEN" \
  /d:sonar.sourceEncoding=UTF-8 \
  /d:sonar.exclusions="**/devops/**,**/load-tests/**,**/AppHost/**,**/Migrations/**" \
  /d:sonar.cs.opencover.reportsPaths="TestResults/**/coverage.opencover.xml" \
  /d:sonar.coverage.exclusions="**/obj/**,**/bin/**,**/tests/**,**/AppHost/**,**/Infrastructure.Mock/**"
```

### Build
```bash
dotnet build HealthPlatform.Api.Mail.sln --configuration Release --verbosity quiet
```

### Test with coverage (OpenCover)
```bash
for proj in \
  tests/mss.mail.domain.tests/mss.mail.domain.tests.csproj \
  tests/mss.mail.application.tests/mss.mail.application.tests.csproj \
  tests/mss.mail.infrastructure.tests/mss.mail.infrastructure.tests.csproj \
  tests/mss.mail.api.tests/mss.mail.api.tests.csproj \
  tests/mss.mail.integration.tests/mss.mail.integration.tests.csproj ; do
  dotnet test "$proj" \
    --configuration Release \
    --collect:"XPlat Code Coverage;Format=opencover" \
    --results-directory TestResults \
    --logger "console;verbosity=minimal"
done
```

### End
```bash
dotnet sonarscanner end /d:sonar.token="$SONAR_TOKEN"
```

### KPI fetch
```bash
metrics="bugs,vulnerabilities,code_smells,coverage,line_coverage,branch_coverage,duplicated_lines_density,ncloc,sqale_index,reliability_rating,security_rating,sqale_rating,security_hotspots"
curl -s -u "$SONAR_TOKEN:" \
  "$SONAR_HOST_URL/api/measures/component?component=$SONAR_PROJECT_KEY&metricKeys=$metrics"
```

Rating mapping : `1=A, 2=B, 3=C, 4=D, 5=E`.

---

## Rules

- The forge NEVER merges the PR — HAG rule 10 always applies.
- **Zero-new-debt** : aucune issue new-code ne peut être laissée non
  traitée, aucun trou de couverture sur le new code ne peut être laissé
  ouvert. Si Phase 1 est bloquée → `questions/` + halt, jamais `/review`.
- Each behavioural fix is preceded by a RED unit test (rule 1). Pour le
  new code, les tests manquants doivent être créés (pas seulement les
  fix de bugs comportementaux).
- Blacklisted rules (`agents/sonar-blacklist.yml`) :
  - **Phase 1 (new code)** : la blacklist NE s'applique PAS. Les findings
    doivent être fix manuellement OU déclencher un halt via `questions/`.
  - **Phase 2 (legacy)** : la blacklist s'applique normalement.
  - S3776 (cognitive complexity) garde sa commande dédiée `/sonar-s3776`,
    y compris pour le new code (auquel cas Phase 1 halt avec une question
    pointant vers `/sonar-s3776`).
- **Feed `conventions/csharp.md`** at the end of every run (Mode A and
  Mode B alike) for each manually-fixed rule likely to recur in fresh code
  — see Step 5. The self-improving loop only works if the feeding is
  systematic.
- Build + full tests MUST pass after each iteration before re-analysis.
- **Phase 1** : aucun cap de fichiers, aucun cap d'itérations. Cap de 100
  issues / itération uniquement pour cadencer les commits.
- **Phase 2** : max 30 fichiers / itération, max 5 itérations / run.
- No `--no-verify` on git commands. No rebase — only merge (rule 4).
- The token is read from `SONAR_TOKEN`, never hardcoded.
- On any unexpected state (file you don't understand, conflict, missing test
  project, etc.), stop and create `questions/sonar-api-mail-{YYYYMMDD}.md`
  rather than improvising.
