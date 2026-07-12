# /stitch-design — Stitch design reference for client-mobile

Usage :
- `/stitch-design {task-id}` — **Mode A (chained)**. Called by `/develop`
  (Step 5c) for the task's `client-mobile` screens, **before** the Ionic code
  is written. Ensures every target screen has a matching design in the Stitch
  project `client-mobile` (reuse if present, **create** if missing), records a
  `## Stitch design log` in `tasks/wip-{task-id}.md`, and returns control to
  `/develop`. Best-effort & non-blocking.
- `/stitch-design {screen-name}` — **Mode B (stand-alone)**. Manual.
  Create or refresh the design of one screen (e.g.
  `/stitch-design mail-compose`). Prints the report (screen id, title,
  screenshot URL) and exits. No task file, no hand-off.

Purpose : make **Stitch the single source of truth for the `client-mobile`
UI design**. The mobile messaging client (Ionic 8 + Angular 20 + Capacitor,
`Client/Mobile/`) gets its screens designed in the Stitch project
`client-mobile` (id `10088502293310567548`, MOBILE) first ; `/develop` then
codes each Ionic screen **against that reference**.

The link between a Stitch screen and an Ionic artifact is the **screen title =
component/page kebab-case name** convention — the file/selector base name
(`inbox`, `mail-list`, `mail-folder-list`, …), not the PascalCase class name.

**Stitch output is a reference, not applied code.** Stitch emits HTML/CSS ;
`/develop` translates the visual + structural intent into Ionic components. No
Stitch HTML is ever pasted into the repo.

**Tooling limitations** (cf. agents/stitch-design.md, diagnostic 2026-07-06) :
1. No **rename** operation — existing-screen renames are done by the human in
   the Stitch UI ; created screens bias their title via the generation prompt
   and the agent logs the actual title + any mismatch to fix.
2. `generate_screen_from_text` **times out at the MCP layer but succeeds
   server-side** — a timeout is an expected outcome, **never retry** (retries
   create duplicate screens).
3. `list_screens` serves a **stale** snapshot (hours late on fresh creations) ;
   `get_project` (`screenInstances`) is the freshness source of truth.

Read `agents/stitch-design.md` and execute the full playbook :

1. Pre-flight : mode detection (task-id → Mode A, name → Mode B), skip cleanly
   when the task has no `client-mobile` scope, resolve the Stitch project
   `client-mobile` by title.
2. Determine the target screens (task mobile scope in Mode A ; the single name
   in Mode B).
3. For each : **snapshot** `get_project` (instance ids + labels + design
   system id) → match kebab-case name on instance labels, then `list_screens`
   titles ⇒ **reuse** (`get_screen` → HTML/CSS + screenshot) ; no match ⇒
   anti-duplicate guard, then **create** : `generate_screen_from_text` **once**
   (MOBILE, design system id, titled with the kebab-case name), tolerate the
   timeout, **detect the new screen by diffing `get_project` instance ids**
   (~2-3 min later, 2-3 spaced attempts max), `get_screen` it. Fallback : log
   the generation prompt for a manual run in the Stitch UI and proceed.
4. Record the `## Stitch design log` (Mode A) and hand back to `/develop`, or
   print the report (Mode B).

Best-effort acceptance : a Stitch/MCP outage or an unmaterialised generation is
**not** a blocker — it is logged (with the prompt for the human) and `/develop`
proceeds without the reference.

## Rules

- Scope : `client-mobile` only, via the Stitch project `client-mobile`. Never
  designs for other repos or Stitch projects.
- Stitch is the **design reference, not code** — never pastes Stitch HTML/CSS
  into `Client/Mobile/`.
- **No git, no source files** : only talks to the Stitch MCP and writes the
  `## Stitch design log` in the task file (Mode A).
- Idempotent : reuse an existing matching screen, never create a duplicate ;
  prefer `edit_screens` over a second create when a refresh is needed.
- **Timeout ≠ échec ; jamais de retry de génération** (source des doublons).
  Détection du résultat par diff des `screenInstances` de `get_project`.
- **`list_screens` n'est pas fiable pour la fraîcheur** — pas de polling en
  boucle (appels lourds, ~8-11k tokens) ; 2-3 lectures espacées max par run.
- Best-effort & non-blocking ; fail-fast (`questions/{task-id}.md`) only on a
  genuine logical blocker (e.g. the `client-mobile` Stitch project no longer
  resolves by title), never on a transient MCP error.
