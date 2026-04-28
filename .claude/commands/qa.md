# /qa — End-to-end QA test run

Usage :
- `/qa` — start backend + frontend in test bypass mode, run the full
  Playwright suite, then stop everything.
- `/qa <playwright-args>` — pass-through to Playwright, e.g.
  - `/qa --grep smoke` — run only tests matching `smoke`
  - `/qa --project chromium` — restrict to one project
  - `/qa --headed` — open the browser window during the run
  - `/qa --headed` with `PW_SLOW_MO=800` exported beforehand — same, but
    every Playwright action is slowed by 800 ms so a human can follow
    along visually
  - `/qa --debug` — Playwright inspector mode (interactive)
  - `/qa --ui` — Playwright UI mode (interactive graphical runner)
- `/qa scaffold` — only create `tests/E2E/` (Playwright project + smoke
  test), do not start the stack or run tests. Useful on first setup.
- `/qa --kill-leftovers` — before starting, free ports 5052 / 7213 / 5295
  by killing any process listening there. Risky — use only when sure.

Purpose : execute end-to-end tests against the full HealthPlatform stack
(api-mail backend + client-blazor frontend) running locally in **test
bypass mode**. The bypass injects a fake authenticated session via
HTTP headers, removing the OIDC dependency for automated tests.

`/qa` is **human-triggered only**. It is NOT part of the autonomous
chain — `/forge` stops at `/review`, and end-to-end validation is the
human's call before invoking `/merge`.

Read `agents/qa.md` and execute the full playbook :

1. Pre-flight (ports free, bypass infra present, Node/npm OK,
   `ASPNETCORE_ENVIRONMENT != Production`)
2. Scaffold `tests/E2E/` if absent (Playwright + 1 smoke test)
3. Start backend (`dotnet run --launch-profile http` on `Api/Mail/src/Api`)
4. Start frontend (`dotnet run --launch-profile https_test` on
   `Client/Blazor/Src/Shell`)
5. Smoke-test the bypass against `GET /api/v1/mail/folders`
6. Run Playwright (forward any args from this command)
7. Stop both processes (always — even on test failure)
8. Report passed/failed/skipped + HTML report path

## Rules

- Read-only on production code. The agent only creates the `tests/E2E/`
  scaffold on first run.
- Never logs credentials (`TestPassword`, `BypassKey`).
- Always tears down both processes, no zombies.
- No git ops on `client-angular` (out of scope for `/qa`).
- No commit, no push, no merge — `/qa` is purely a runner.

## When NOT to use `/qa`

- During `/develop` or `/review` — those handle unit + integration tests
  via `dotnet test`. `/qa` is for end-to-end validation across the full
  stack.
- Against Production. The bypass is locked to dev / test environments.
- To run Angular tests — those live in the Angular Nx workspace and are
  the human's domain (TFS, code-only mode).
