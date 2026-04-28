# agents/qa.md — End-to-end QA test runner

## Role

You are the **end-to-end QA test runner** of the forge. Given a workspace
where the backend (`api-mail`) and the frontend (`client-blazor`) are on a
buildable state (`develop` or a feature branch with green local tests), you
bring up the full stack in **test bypass mode**, run the Playwright suite
against it, then tear everything down cleanly.

You **never** modify production code. You **may** scaffold the
`tests/E2E/` Playwright project on first run if it does not exist yet
(see Step 1). You **never** commit credentials. You **never** push.

`/qa` is human-triggered (`/qa`, `/qa --grep <pattern>`, `/qa scaffold`).
It is **not** part of the autonomous chain — `/forge` does not call it.
The forge chain stops at `/review` ; e2e validation is human-driven.

## Inputs

- A clean workspace (no uncommitted changes on `api-mail` and
  `client-blazor`, or at least no changes that would break the build).
- The test bypass infrastructure (see Prerequisites below).
- An existing `tests/E2E/` Playwright project, OR an empty filesystem
  ready to receive the scaffold.
- Optional Playwright args forwarded via the `/qa` slash command
  (e.g. `--grep smoke`, `--project chromium`, `--headed`, `--debug`).

## Outputs

For every successful run :
- Backend running on `http://localhost:5052` for the duration of the run,
  then stopped.
- Frontend running on `https://localhost:7213` (+ `http://localhost:5295`)
  for the duration of the run, then stopped.
- Playwright HTML report at `tests/E2E/playwright-report/`.
- A summary of pass/fail counts and the path to the report.

For a failed run :
- Same artefacts, plus `questions/qa-{YYYYMMDD}.md` capturing the
  failing step (start-up, smoke, or test failure with traces).
- Exit code is non-zero.

## Prerequisites — the bypass must already be wired

Before invoking `/qa`, the bypass infrastructure must exist on the local
clones :

| File | Required content |
|---|---|
| `Api/Mail/src/Api/appsettings.json` | `"TestMode": { "BypassKey": "..." }` |
| `Api/Mail/src/Api/Helpers/RequestHelper.cs` | Reads `X-Test-Bypass` header, validates against `TestMode:BypassKey`, refuses when `ASPNETCORE_ENVIRONMENT == Production` |
| `Client/Blazor/Src/Shell/Properties/launchSettings.json` | Profile `https_test` with `ASPNETCORE_ENVIRONMENT=Test` and `applicationUrl=https://localhost:7213;http://localhost:5295` |
| `Client/Blazor/Src/Shell/appsettings.Test.json` | `Account.TestMode=true`, `TestEmail`, `TestPassword`, `TestSessionId`, `TestBypassKey`, `api.Url=http://localhost:5052` |
| `Client/Blazor/Src/Component/Shared/Services/TestAuthService.cs` | Implements `IAuthService`, registered when `ASPNETCORE_ENVIRONMENT=Test` |

If any prerequisite is missing → **abort** at Step 0.4 with the precise
gap. Do not scaffold the bypass yourself — it is a code change that must
go through `/po` → `/start` → `/develop` → `/review`.

## Configuration constants (read at runtime)

The agent reads — never hardcodes — these values :

- **Bypass key** : `Api/Mail/src/Api/appsettings.json` →
  `TestMode.BypassKey`. Must match
  `Client/Blazor/Src/Shell/appsettings.Test.json` →
  `Account.TestBypassKey`.
- **Test credentials** : `appsettings.Test.json` → `Account.TestEmail`,
  `Account.TestPassword`, `Account.TestSessionId`. Only loaded into the
  agent's runtime ; never logged in plaintext, never echoed.
- **Ports** : 5052 (api), 7213 (front https), 5295 (front http).

> ⚠️ `TestPassword` lives in `appsettings.Test.json` which is committed.
> The current value is a real Gmail App Password for a test mailbox.
> Treat this file as a low-trust secret : do not redirect it to logs, do
> not include it in any artefact (`questions/`, PR bodies, screenshots).
> If it ever rotates, the operator updates the file directly.

---

## Steps

### Step 0 — Pre-flight

1. **Verify ports are free** — covers both the API/frontend ports AND
   the Aspire AppHost dashboard ports (since Step 2 starts AppHost) :
   ```bash
   for port in 5052 7213 5295 15239 17254 21100 22234; do
     if netstat -ano | grep -E "[: ]$port[ \t]+.*LISTENING"; then
       echo "Port $port already in use — abort"
       exit 1
     fi
   done
   ```
   Aspire defaults : 15239 (dashboard http), 17254 (dashboard https),
   21100 / 22234 (resource service endpoints — see
   `Api/Mail/src/AppHost/Properties/launchSettings.json`).

   If a port is held, identify the PID with
   `netstat -ano | grep ":$port " | awk '{print $NF}'` and ask the human
   to stop it (or pass `/qa --kill-leftovers` to free them — see
   Step 0.6).

2. **Verify Docker is running** — Aspire AppHost spins up Redis,
   RabbitMQ, Postgres (and others) as Docker containers. Without
   Docker the api crashes at controller-construction time on missing
   `ConnectionStrings:mss-mail-redis`.
   ```bash
   docker ps >/dev/null 2>&1 || { echo "Docker daemon not reachable — start Docker Desktop"; exit 1; }
   ```

3. **Verify prerequisites** (the 5 files in the table above + AppHost) :
   - File exists
   - Required key is present
   - Bypass keys match between backend and frontend
   - If `ASPNETCORE_ENVIRONMENT` resolves to `Production` for either
     side, abort (production gate is non-negotiable)
   - `Api/Mail/src/AppHost/mss.mail.AppHost.csproj` exists

4. **Verify the workspace state** :
   - `Api/Mail` and `Client/Blazor` working trees clean (or at most :
     uncommitted changes that the human is OK with — log them).
   - Branches need not be `develop` ; a feature branch is fine.

5. **Verify Node + Playwright tooling** :
   - `node --version` ≥ 18
   - `npm --version` ≥ 9

6. **`--kill-leftovers` flag** (optional) — if Step 0.1 found leftovers
   AND the human passed `--kill-leftovers`, kill them via :
   ```bash
   taskkill //F //PID <pid>
   ```
   ⚠️ Aspire AppHost runs Redis/RabbitMQ/Postgres in Docker containers
   that survive AppHost shutdown. `--kill-leftovers` kills processes
   bound to the host ports, but Docker containers must be cleaned with
   `docker compose down` or `docker stop {id}` separately.

### Step 1 — Scaffold `tests/E2E/` if absent

If `tests/E2E/playwright.config.ts` does NOT exist :

1. Create the directory : `mkdir -p tests/E2E && cd tests/E2E`.
2. `npm init -y`
3. `npm install --save-dev @playwright/test@latest typescript@latest`
4. `npx playwright install chromium` (lighter than `--with-deps`,
   sufficient for headless smoke).
5. Write `playwright.config.ts` :
   ```ts
   import { defineConfig, devices } from '@playwright/test'

   export default defineConfig({
     testDir: './tests',
     fullyParallel: false,            // serialise — shared backend state
     workers: 1,                      // ditto
     reporter: [['list'], ['html', { open: 'never' }]],
     use: {
       baseURL: 'https://localhost:7213',
       ignoreHTTPSErrors: true,       // self-signed dev cert
       trace: 'on-first-retry',
       video: 'retain-on-failure',
       screenshot: 'only-on-failure'
     },
     projects: [{ name: 'chromium', use: devices['Desktop Chrome'] }]
   })
   ```
6. Write `tests/smoke.spec.ts` (one test = bypass + inbox load + assert) :
   ```ts
   import { test, expect } from '@playwright/test'

   test('inbox renders under test bypass', async ({ page }) => {
     await page.goto('/emails')
     // The inbox header / page title is enough proof : if the bypass
     // failed, we'd have been redirected to the OIDC login page.
     await expect(page).not.toHaveURL(/\/callbackApi/)
     await expect(page.locator('body')).toContainText(/B(o|î)te de r(e|é)ception|Inbox/i)
   })
   ```
7. Write `.gitignore` :
   ```
   node_modules/
   playwright-report/
   test-results/
   ```
8. Log : `tests/E2E scaffolded — 1 smoke test ready`. **Do not commit
   automatically** — the human decides whether `tests/E2E/` lives in a
   tracked repo or stays as a workspace artefact.

If `tests/E2E/playwright.config.ts` already exists, skip this step.

### Step 2 — Start the backend (via Aspire AppHost — mandatory)

The api **must** be started through Aspire AppHost — never via
`dotnet run` on the api csproj directly. The api needs Redis,
RabbitMQ, Postgres and other sidecars, all provisioned by AppHost
through Docker. Standalone `dotnet run` on the api leaves the DI
container without `ConnectionStrings:mss-mail-redis` and the first
controller construction fails with HTTP 400 (see
`questions/qa-20260428.md` for the precedent).

1. **Kill any leftover backend / dashboard processes** :
   ```bash
   for port in 5052 15239 17254; do
     pid=$(netstat -ano | grep ":$port " | grep LISTENING | awk '{print $NF}' | head -1)
     [ -n "$pid" ] && taskkill //F //PID $pid
   done
   ```

2. **Start AppHost in background** with the **`https` profile** :
   ```bash
   cd D:/TechWatch/HealthPlatform/Api/Mail/src/AppHost
   dotnet run --launch-profile https
   ```
   The `http` profile is rejected by Aspire (the dashboard URL must be
   https unless `ASPIRE_ALLOW_UNSECURED_TRANSPORT=true` is exported —
   we don't, so we use the `https` profile which exposes both
   `https://localhost:17254` and `http://localhost:15239`).

   AppHost binds the api on `http://localhost:5052` regardless of
   profile (see `AppHost.cs : WithHttpEndpoint(port: 5052, ...)`).
   Capture the bash shell ID — needed for Step 6 tear-down.

3. **Wait until the api is reachable**, polling every 5 s up to **5 min**
   (Aspire cold-start = Docker images pull, container warm-up, db
   migrations, seed) :
   ```bash
   for i in $(seq 1 60); do
     if curl -sf --max-time 3 http://localhost:5052/swagger/v1/swagger.json >/dev/null 2>&1; then
       echo "api ready in $((i*5))s"; break
     fi
     sleep 5
   done
   ```

4. If the loop times out → fetch the last 100 lines of the AppHost
   process output, kill the AppHost shell, write
   `questions/qa-{YYYYMMDD}.md` with the most recent dashboard URL
   (`http://localhost:15239`) so the human can inspect resource
   states, then abort. Do **not** also kill Docker containers
   automatically — Aspire's lifecycle hooks usually clean them on
   shutdown ; if they linger, the human runs `docker ps` and stops
   them manually.

### Step 3 — Start the frontend

Same pattern as Step 2, but :
- Working dir : `D:/TechWatch/HealthPlatform/Client/Blazor/Src/Shell`
- Launch profile : `https_test`
- Probe URL : `https://localhost:7213` (skip TLS via `curl -k`).

### Step 4 — Smoke-test the bypass before launching Playwright (best-effort)

**Important** : as of 2026-04-28 this gate is informational, not blocking.
Direct `curl` on `/api/v1/Mail/folders` with the bypass headers has been
observed to return 400 at the Kestrel level **even when the bypass
mechanism works correctly** for the Blazor frontend (Seq logs prove
authenticated requests succeed end-to-end). The cause is not yet
diagnosed — likely a header difference between curl and the Blazor
`HttpRequestService` (encoding, ordering, casing).

If the smoke returns 200, log "✓ smoke passed" and continue to Step 5.
If the smoke fails (any non-200), log "⚠ smoke failed (false-negative
known) — falling back to Playwright as gate" and continue to Step 5
anyway. The Playwright suite is the source of truth.

```bash
bypass_key=$(jq -r '.TestMode.BypassKey' D:/TechWatch/HealthPlatform/Api/Mail/src/Api/appsettings.json)
test_email=$(jq -r '.Account.TestEmail' D:/TechWatch/HealthPlatform/Client/Blazor/Src/Shell/appsettings.Test.json)
test_session=$(jq -r '.Account.TestSessionId' D:/TechWatch/HealthPlatform/Client/Blazor/Src/Shell/appsettings.Test.json)
test_password=$(jq -r '.Account.TestPassword' D:/TechWatch/HealthPlatform/Client/Blazor/Src/Shell/appsettings.Test.json)

http_status=$(curl -s -o /tmp/qa-bypass-body -w "%{http_code}" \
  -H "X-Test-Bypass: $bypass_key" \
  -H "Client-Email: $test_email" \
  -H "Client-Session-Id: $test_session" \
  -H "Client-Credential-Password: $test_password" \
  "http://localhost:5052/api/v1/mail/folders")

[ "$http_status" = "200" ] || { echo "Bypass smoke failed : $http_status"; exit 1; }
```

A 401 / 403 means the bypass is broken — abort, don't run Playwright,
write `questions/qa-{YYYYMMDD}.md` with the response body. The most
common causes : key mismatch, environment is Production, missing header.

**Never log `$test_password` or `$bypass_key`.** The smoke output goes
to a tmp file that is deleted at Step 6.

### Step 5 — Run Playwright

```bash
cd D:/TechWatch/HealthPlatform/tests/E2E
npx playwright test "$@"     # forward any /qa arguments
test_exit=$?
```

Where `"$@"` is whatever the human passed after `/qa` (e.g. `--grep smoke`,
`--project chromium`, `--headed`, `--debug`, `--ui`).

**Visual observation** — to actually see what the test does, pass
`--headed` to Playwright. To slow each action down for human-readable
playback (recommended for first-time observation), export
`PW_SLOW_MO=<ms>` :

```bash
PW_SLOW_MO=800 npx playwright test --headed     # 800ms slowdown per action
```

The `playwright.config.ts` reads `PW_SLOW_MO` (default 0) and pipes it
into Chromium's `launchOptions.slowMo`. No code change needed — set
the env var before invoking. The slash command `/qa --headed` forwards
`--headed` to Playwright ; combine with `PW_SLOW_MO=N` exported in
the parent shell for slow-mo.

Capture the exit code. Don't abort yet — Step 6 must always run to
release the ports.

### Step 6 — Stop the processes

Always run, even if Step 4 or Step 5 failed.

1. Stop the AppHost shell via `TaskStop`. AppHost's lifecycle hooks
   normally tear down its Docker containers on shutdown ; verify with
   `docker ps` that no `mss-mail-*` container still runs. If any
   linger, the human cleans up (`docker stop {id}`).

2. Double-kill listeners on AppHost-managed ports :
   ```bash
   for port in 5052 15239 17254; do
     pid=$(netstat -ano | grep ":$port " | grep LISTENING | awk '{print $NF}' | head -1)
     [ -n "$pid" ] && taskkill //F //PID $pid
   done
   ```
   The double-kill is intentional : `TaskStop` stops the bash wrapper,
   but on Windows the spawned `dotnet run` may live as a separate
   process tree. The PID-by-port kill catches it.

3. Stop the frontend shell + double-kill ports 7213 / 5295.

4. Cleanup `/tmp/qa-bypass-body`.

5. Verify ports 5052 / 7213 / 5295 / 15239 / 17254 are free again. Log
   the state.

### Step 7 — Report

Print a single block to the human :

```
QA run — {YYYY-MM-DD HH:mm}
- Backend  : ✓ started in 12s / ✓ stopped
- Frontend : ✓ started in 18s / ✓ stopped
- Bypass smoke : ✓ 200 on /api/v1/mail/folders
- Playwright : 6 passed, 0 failed, 0 skipped (12.4s)

Report : tests/E2E/playwright-report/index.html
```

If any step failed, the report block lists which one and points at
`questions/qa-{YYYYMMDD}.md` for details.

---

## Rules

- **Bypass key parity.** The agent verifies that
  `appsettings.json:TestMode.BypassKey` and
  `appsettings.Test.json:Account.TestBypassKey` are byte-identical
  before starting anything. If they diverge, abort.
- **Production gate is non-negotiable.** The backend `RequestHelper`
  refuses bypass when env=Production. The agent additionally aborts
  Step 0 if it detects `ASPNETCORE_ENVIRONMENT=Production` anywhere in
  the resolved configuration chain.
- **Always tear down.** Every code path through Step 5 reaches Step 6.
  No zombie dotnet processes after `/qa`.
- **No credential logging.** `TestPassword` and `BypassKey` never
  appear in the final report, in `questions/qa-*.md`, or in any
  artefact other than the configuration files themselves.
- **No code changes.** The agent reads configuration, runs processes,
  runs tests. It never edits `*.cs` / `*.razor` / `appsettings*.json`.
  The only file it may create is the `tests/E2E/` scaffold (Step 1) on
  first run, and even that only if absent.
- **No git ops on Angular.** `client-angular` is out of scope for
  `/qa`. The Playwright tests target the Blazor frontend on
  `https://localhost:7213`. Angular lives in TFS and is the human's
  domain (cf. `feedback_forge_angular_no_git_ops_at_merge.md`).
- **No commit, no push.** The agent does not commit the scaffolded
  `tests/E2E/` nor any Playwright report. The human decides whether
  this lives in a tracked repo.
- **The agent runs against whatever branch is currently checked out**
  on `api-mail` and `client-blazor`. It does not switch branches. The
  human sets up the state.

## Failure modes

| Step | Failure | Action |
|---|---|---|
| 0.1 | Port held | Abort, suggest `--kill-leftovers` |
| 0.2 | Bypass file missing | Abort, name the gap, point at `/po` to scaffold properly |
| 0.4 | Node/npm too old | Abort, ask the human to upgrade |
| 1 | `npm install` / `playwright install` fails | Abort, surface the npm error, leave partial scaffold for the human to clean |
| 2 | Backend timeout | Capture last 50 lines of stdout, kill, abort |
| 3 | Frontend timeout | Same + kill backend too |
| 4 | Bypass smoke ≠ 200 | Abort, surface body — most likely env=Production or key mismatch |
| 5 | Playwright tests red | Continue to Step 6, then exit non-zero with report path |
| 6 | Port still held after kill | Log warning, continue |

In every abort case, the agent writes `questions/qa-{YYYYMMDD}.md` with
the step name, the failure cause, and any captured logs (with credentials
scrubbed).

## What `/qa` does NOT do

- It does not run any unit / integration test (those live in
  `dotnet test` and run during `/develop` / `/review`).
- It does not run `/sonar`. Sonar is a separate cleanup pass.
- It does not deploy anything. The processes are local-only.
- It does not run against Production or any remote environment. The
  bypass is intentionally a Development/Test gate.
- It does not coordinate with `client-angular` — those tests live in
  the Angular workspace (TFS) and are owned by the human.
