# merge-task-037 — Uncommitted changes block merge

**Status** : `/merge task-037 --i-tested` aborted on **safety gate 6**
(working tree of a target repo has uncommitted changes outside of
`client-angular`). Atomic batch — **no PR was merged**.

## Context

Run : `/merge task-037 --i-tested`
Date : 2026-05-15
Trigger : human-invoked after testing the US end-to-end (HAG, rule 10).

PRs in scope :
- dtos-mss #23 — `awaiting-human-merge`, MERGEABLE, CI green
- api-mail #57 — `awaiting-human-merge`, MERGEABLE, CI green (no checks ≠ red)
- client-blazor #52 — `awaiting-human-merge`, MERGEABLE, CI green
- client-angular — code-only, out of scope for `/merge`

Safety gates 2–5 passed on all three pushable PRs. Gate 6 failed.

## Blocker

Repo `api-mail`, branch `feat/task-037-mss-account-onboarding` (the PR
#57 branch — same as the remote head) has **uncommitted local
modifications** :

```
 M src/Api/Middleware/UserContextEnricherMiddleware.cs
 M tests/mss.mail.api.tests/Middleware/UserContextEnricherMiddlewareTests.cs
```

Diff summary : 47 insertions / 9 deletions across the two files.

## What the uncommitted diff does

The change **switches the middleware bypass from attribute-based to
path-prefix-based** :

- Before (currently on PR #57) : middleware looks up
  `AllowMissingMssEmailAttribute` on the endpoint metadata and skips the
  strict `mssEmail` cross-check when present. The new
  `mss-imap-test` controller carries the attribute.
- After (in the working tree) : middleware exposes an internal
  `ExcludedPathPrefixes` array hard-coded with
  `/api/v1/account/mss-imap-test`. The attribute lookup is dropped, the
  call to `ApplyAuthenticatedUserAsync` is hard-wired with
  `allowMissingMssEmail: false`, and an `IsExcludedPath(PathString)`
  helper is added. The companion test is rewritten to drop the
  endpoint-metadata fixture and instead set
  `context.Request.Path = "/api/v1/account/mss-imap-test"`.

Either approach reaches the same functional outcome (the onboarding
endpoint must be reachable by a JWT without `mssEmail`), but they differ
materially :

| Aspect | Attribute (PR #57) | Path prefix (uncommitted) |
|---|---|---|
| Coupling | Endpoint declares its own opt-out | Middleware owns the allow-list |
| Discoverability | Visible on the controller | Hidden inside the middleware |
| Drift risk | Endpoint can be moved/renamed without losing the opt-out (attribute travels with the action) | Renaming/relocating the route silently breaks the bypass |
| Adding another exempt route | Add `[AllowMissingMssEmail]` on the new endpoint | Edit the array in the middleware (centralised but invasive) |

The two are *not* equivalent in maintenance terms. This isn't a stylistic
nit — it's an architectural decision.

## Question for the human

1. Is the uncommitted diff intended to **replace** the attribute-based
   bypass that PR #57 introduced ? (Or was it an exploratory edit you
   forgot to discard ?)

2. If intended :
   - The diff should be **committed and pushed to PR #57** before
     `/merge` runs again. Doing so will re-trigger CI ; let it go green,
     then re-run `/merge task-037 --i-tested`.
   - The `AllowMissingMssEmailAttribute` type currently shipped on PR
     #57 becomes dead code. Decide whether to remove it as part of the
     same commit or leave it for a follow-up.
   - Tests already updated in the working copy — good. No other test
     touches `AllowMissingMssEmailAttribute` in the diff, but a grep
     before commit is worth it.

3. If unintended : `git checkout -- src/Api/Middleware/UserContextEnricherMiddleware.cs tests/mss.mail.api.tests/Middleware/UserContextEnricherMiddlewareTests.cs`
   in `Api/Mail/`, then re-run `/merge task-037 --i-tested`.

## Why the gate exists (reminder)

Safety gate 6 prevents `/merge` from squash-merging the **remote** state
while the **local** state of the same branch carries unmerged work : a
silent loss after `git checkout develop && git pull` would discard the
uncommitted edits. The atomic-batch rule (rule 5 of the spec) then
refuses to merge any PR in the set until the offender is clean.

## Next step

Resolve the api-mail working tree (commit + push, or discard), then
re-run :

```
/merge task-037 --i-tested
```
