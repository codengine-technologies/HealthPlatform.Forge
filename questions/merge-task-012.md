# merge-task-012.md — `/merge` aborted, safety gate 6

`/merge task-012 --i-tested` was invoked on 2026-04-29 but **safety gate 6
(no uncommitted changes on pushable repos)** failed. No PR was merged
(atomic — all-or-nothing).

## Other gates

| Gate | dtos-mss #11 | api-mail #33 | client-blazor #38 |
|---|---|---|---|
| `--i-tested` flag | ✓ | ✓ | ✓ |
| Label not `awaiting-us-completion` | ✓ (`awaiting-human-merge`) | ✓ (`awaiting-human-merge`) | ✓ (`awaiting-human-merge`) |
| `reviewDecision` | empty (no blocker) | empty (no blocker) | empty (no blocker) |
| `mergeable` | MERGEABLE | MERGEABLE | MERGEABLE |
| CI | ✓ build pass | no checks reported | ✓ build pass (docker skipped) |
| Working tree clean | ✓ | ✗ **dirty** | ✗ **dirty** |

→ Only the working-tree gate fails. Everything else is green.

## Uncommitted changes

### api-mail (branch `feat/task-012-rattachement-patient-visuel`)

`src/Infrastructure/Repository/MailRepository.cs` (1 line) — flips
`Logger.LogInformation(ex, ...)` to `Logger.LogError(ex, ...)` in the
"updated mail content" exception fallback path (line 203). This looks
like a genuine bug fix you spotted during manual testing — the original
log called `LogInformation` while passing an exception, which mismatches
the severity.

```diff
-                    Logger.LogInformation(ex, "[DB] 💾 Updated mail content ...");
+                    Logger.LogError(ex, "[DB] 💾 Updated mail content ...");
```

### client-blazor (branch `feat/task-012-rattachement-patient-visuel`)

Three files :

1. `Src/Modules/Mss/Plugin/Components/MailHeader.razor` — adds a
   conditional CSS class `patient-name-qualified` when
   `doc.PatientId.HasValue` is true.
2. `Src/Modules/Mss/Plugin/Components/MailHeader.razor.css` — defines
   that class : lifts the gray opacity, switches to the primary brand
   color, font-weight 600, with a comment tying it to task-012.
3. `Src/Shell/HealthPlatform.Host.Shell.csproj.user` — IDE local
   settings (should likely be in `.gitignore`).

The Razor + CSS changes look like a deliberate visual polish you added
during the human test pass — qualified patients (auto-attached via INS)
now stand out in the inbox vs. non-qualified rows. They are coherent
with the task-012 scope.

## What you can do

These edits look like a bona-fide tail of task-012, not stray noise.
Three options :

1. **Commit on the feature branch and re-merge** (recommended if you
   want them in the same PR) :
   ```bash
   cd Api/Mail
   git add src/Infrastructure/Repository/MailRepository.cs
   git commit -m "fix(mail): use LogError for exception in update-content fallback (task-012)"
   git push
   cd ../../Client/Blazor
   git add Src/Modules/Mss/Plugin/Components/MailHeader.razor Src/Modules/Mss/Plugin/Components/MailHeader.razor.css
   git commit -m "feat(mss): highlight qualified patient name in inbox (task-012)"
   git push
   ```
   The PR auto-updates, CI re-runs, then re-invoke `/merge task-012 --i-tested`.

2. **Stash** if you'd rather keep them as a separate follow-up :
   ```bash
   cd Api/Mail && git stash push -m "logerror-tail" -- src/Infrastructure/Repository/MailRepository.cs
   cd ../../Client/Blazor && git stash push -m "qualified-name-polish" -- Src/Modules/Mss/Plugin/Components/MailHeader.razor Src/Modules/Mss/Plugin/Components/MailHeader.razor.css
   ```
   Then re-invoke `/merge task-012 --i-tested`. Pop the stashes later
   on a new branch / task.

3. **Discard** if these were experiments :
   ```bash
   cd Api/Mail && git checkout -- src/Infrastructure/Repository/MailRepository.cs
   cd ../../Client/Blazor && git checkout -- Src/Modules/Mss/Plugin/Components/MailHeader.razor Src/Modules/Mss/Plugin/Components/MailHeader.razor.css
   ```

The `.csproj.user` is unrelated to the merge — git-ignore it (or
discard locally) regardless of which option you pick.

## Status

- No PR merged.
- Branches untouched.
- Task still `done-task-012.md`.
- `/merge` will succeed once the working trees are clean.
