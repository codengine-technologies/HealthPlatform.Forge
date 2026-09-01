# /qa — End-to-end visual QA run (client-mobile, login PSC humain)

Usage :
- `/qa` — start the real backend (Aspire AppHost) + serve the mobile app
  (`ng serve`), run the Playwright suite **headed**, let a human do the
  Pro Santé Connect login by hand, capture every reachable mobile screen,
  then stop everything.
- `/qa <playwright-args>` — pass-through to Playwright, e.g.
  - `/qa --grep tour` — run only tests matching `tour`
  - `PW_SLOW_MO=800 /qa` (env exported beforehand) — slow each action by
    800 ms so a human can follow along visually
  - `/qa --debug` — Playwright inspector mode (interactive)
  - `/qa --ui` — Playwright UI mode (interactive graphical runner)
- `/qa --kill-leftovers` — before starting, free ports 4200 / 5052 / 7012 /
  15239 / 17254 by killing any process listening there. Risky — use only
  when sure.

Purpose : execute end-to-end **visual** tests against `client-mobile` (Ionic /
Angular mobile messaging client) running on the **real backend**, with the
**Pro Santé Connect login performed by a human** at the start of the run. The
suite captures a 390×844 screenshot per screen for human review — no pixel
comparison, blank/crash gate only.

`/qa` is **human-triggered only**. It is NOT part of the autonomous chain —
`/forge` stops at `/review`. The suite is **headed** and needs a human login,
so it can never run unattended.

> The fixture-mocked, no-auth headless captures live separately in
> `/verify-visual` (`Tools/visual-verify/`). `/qa` is the **real PSC auth**
> path. The old Blazor `tests/E2E/` bypass suite was removed by task-170.

## GARDE-FOU données de santé (non négociable)

A real PSC login opens a **real MSSanté mailbox** → a screenshot can contain
patient data (nom/INS, contenu MSSanté). Run **only** with a **PSC test
account** whose mailbox holds **anonymized synthetic** messages. Screenshots
are git-ignored ; never commit one without proof it carries no DSCP. Never
run against production.

Read `agents/qa.md` and execute the full playbook :

1. Pre-flight (ports free, Docker up, Node/npm OK, suite present, env ≠ Production)
2. Start the backend via Aspire AppHost (`dotnet run --launch-profile https`
   on `Api/Mail/src/AppHost`, api on `https://localhost:7012` / `http://localhost:5052`)
3. Serve the mobile app (`npm start` on `Client/Mobile`, `http://localhost:4200`)
4. Run Playwright headed (`npm run e2e`) — a human does the PSC login in the
   opened window ; the suite waits for `ion-tabs` then captures each screen
5. Tear down app + backend + Docker sidecars (always — even on failure)
6. Report captured screens / blank-crash failures + HTML report path

## Rules

- Read-only on production code. `/qa` never edits the suite (it lives in
  `Client/Mobile/e2e/`, delivered by task-170).
- Real PSC login, human-assisted — never automated, never a stored secret,
  never a bypass. Test mailbox only.
- Always tears down app + backend + Docker containers, no zombies.
- No commit, no push, no merge — `/qa` is purely a runner. Screenshots stay
  git-ignored.
- client-mobile only — no Angular, no Blazor.

## When NOT to use `/qa`

- During `/develop` or `/review` — those handle unit tests (`ng test`).
- For headless fixture captures — that's `/verify-visual` (in the autonomous chain).
- Against Production or any remote environment. Local dev only.
