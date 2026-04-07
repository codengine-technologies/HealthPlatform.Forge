# /kickoff — Bootstrap a new project for the forge

Execute the full kickoff process in 5 phases.

---

## Phase 1: Detect project environment

Scan the current directory to auto-detect:
- **Stack**: package.json (Node/TS), *.csproj (.NET), requirements.txt (Python), go.mod (Go), Cargo.toml (Rust)
- **Build command**: npm run build, dotnet build, cargo build, go build, etc.
- **Test command**: npm test, dotnet test, pytest, go test, cargo test, etc.
- **Lint command**: npm run lint, dotnet format, ruff check, golangci-lint, etc.
- **CI/CD**: .github/workflows/, .gitlab-ci.yml, Jenkinsfile
- **Module structure**: src/, lib/, packages/, modules/ patterns
- **Frontend framework**: Next.js, React, Vue, Svelte, etc.
- **Design system**: shadcn/ui, MUI, Chakra, Vuetify, etc.

Present findings to the user. Ask them to confirm or correct.

## Phase 2: PO Q&A — understand the project

Read `agents/po.md` and lead a structured Q&A:
1. Ask the human to describe their project (what, who, why)
2. Understand all modules, user roles, business rules
3. Propose a module breakdown — get validation
4. Identify frozen files/directories (core infra that shouldn't be modified)
5. Identify architecture specs or constraints

DO NOT skip the Q&A. DO NOT assume business rules. ASK until you have enough to write specs.

## Phase 3: Instantiate agent templates

Using the detected stack from Phase 1, instantiate agent templates from `templates/agents/`:

```
templates/agents/dev.md.template      → .claude/agents/dev.md
templates/agents/qa.md.template       → .claude/agents/qa.md
templates/agents/po.md.template       → .claude/agents/po.md
templates/agents/architect.md.template → .claude/agents/architect.md
templates/agents/ux-designer.md.template → .claude/agents/ux-designer.md
templates/agents/evaluator.md.template  → .claude/agents/evaluator.md
```

Replace variables:
- `{STACK}` → detected stack (e.g., "Node.js 20, TypeScript, Next.js 15")
- `{BUILD_CMD}` → detected build command
- `{TEST_CMD}` → detected test command
- `{LINT_CMD}` → detected lint command
- `{MODULE_STRUCTURE}` → detected module layout
- `{FRONTEND_STACK}` → detected frontend framework
- `{DESIGN_SYSTEM}` → detected design system
- `{TEST_FRAMEWORK}` → detected test framework (jest, xUnit, pytest, etc.)
- `{E2E_TOOL}` → detected E2E tool (Playwright, Cypress, etc.)
- `{ARCHITECTURE_SPEC}` → path to architecture spec if found
- `{FROZEN_FILES}` → list from Phase 2

Also copy `agents/orchestrator.md` → `.claude/agents/orchestrator.md` (no variables, it's universal).

## Phase 4: Generate project files

1. **CLAUDE.md** — instantiate `templates/claude-md-template.md` with detected values
2. **.claude/settings.json** — create with hooks (guard-shared, verify-before-push, guard-feature)
3. **tasks/** — create directory
4. **questions/** — create directory
5. **.claude/commands/** — copy forge commands (forge.md, status.md, dev.md, po.md, kickoff.md)

## Phase 5: Build backlog

Using the PO Q&A from Phase 2:
1. Write all `.feature` files (pure natural language, zero tech)
2. Create all task files (`tasks/todo-*.md`) with dependencies
   - Each task MUST include a `## Definition of Done` section with concrete, binary criteria
   - DOD criteria must be verifiable by the Evaluator agent (no subjective criteria like "clean code")
   - At minimum: build passes, tests pass, Gherkin scenarios GREEN
   - For frontend tasks: add i18n, data-testid, responsive checks as applicable
   - For backend tasks: add unit test coverage, contract alignment checks as applicable
3. Present the complete backlog with dependency graph
4. Get human validation

Once validated → the project is ready for `/forge` or `/loop 15m /forge`.
