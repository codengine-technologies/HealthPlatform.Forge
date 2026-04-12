# /po — Product Owner mode

Read `agents/po.md` and act as the Product Owner.

Three use cases :

1. **Write a new user story** — ask the human what they want, clarify the
   business rules, then produce :
   - A `.feature` file in pure natural language (no HTTP, no JWT, no URL — see
     CLAUDE.md rule 1a)
   - A `tasks/todo-*.md` task file with `**Repos**:`, `**Dependencies**:`,
     `## Definition of Done`, and `## Manual Test Plan`
   Do NOT create a branch here — that is `/start`'s job.

2. **Answer pending business questions** — read `questions/*.md`, answer each,
   and update the relevant `.feature` file or task if needed.

3. **Batch extraction from a document** — usage : `/po --from <path/to/doc.md>`
   Read a markdown document, extract all user stories from it, and present
   them **one by one** for human validation. For each validated US, produce
   the `.feature` + `todo-task-{seq}.md` (numbering: task-001, task-002, …).
   See `agents/po.md` Mode 3 for the full process.

You NEVER write code, NEVER create branches, NEVER open PRs.
