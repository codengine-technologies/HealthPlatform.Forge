# /forge — Lean forge cycle

Read `agents/orchestrator.md` and execute the lean cycle :

1. Scan `tasks/todo-*.md`, `tasks/wip-*.md`, `tasks/review-*.md`, `tasks/done-*.md`
2. Scan `questions/*.md` and open PRs per active repo
3. Print a short status (≤ 15 lines)
4. For each `tasks/review-*.md` → invoke `/review {task-id}`
5. List PRs waiting human merge (label `awaiting-human-merge`)
6. Stop. **Do NOT hunt for extra work.** Idle is allowed.

The forge is limited to **4 actions** : PO / start / validate / PR. Nothing else.
