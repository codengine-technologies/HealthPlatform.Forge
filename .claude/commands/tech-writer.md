# /tech-writer — Maintain the living EPIC documentation

Read `agents/technical-writer.md` and act as the Technical Writer.

## Usage

- `/tech-writer {epic-id}`
  Incremental update (Mode 1) or retro-generation (Mode 2 if the EPIC doc does
  not exist yet). Scans `tasks/*-*.md` for `**Epic**: {epic-id}`, rebuilds the
  writer-owned sections of `docs/epics/E{NNN}-{slug}.md`, preserves the
  human-authored sections.

- `/tech-writer {epic-id} --refresh`
  Full refresh (Mode 3). Rebuilds every writer-owned section from scratch.
  Human sections (Vision, Objectifs métier, Acteurs, Contraintes, Hors
  périmètre) are still preserved.

## Examples

```
/tech-writer E001
/tech-writer E001 --refresh
```

## Behaviour

- Produces **exactly one file** : `docs/epics/E{NNN}-{slug}.md`.
- Idempotent — two runs back-to-back produce identical output.
- Writes nothing and asks for clarification if :
  - No task declares `**Epic**: {epic-id}`
  - The slug cannot be resolved (no existing file, no `**EpicTitle**:`)
  - Two tasks claim the same feature id
  - A dependency cannot be resolved to a known feature id

## Invocation by other commands

`/review` calls `/tech-writer {epic-id}` automatically at the end of its
cycle (after the PRs are opened and the task is moved to `done-*`), provided
the task file declares `**Epic**:`. If the field is absent, `/review` skips
the call and reports "no EPIC linked — skipped tech-writer".

The writer never writes code, never creates branches, never opens PRs.
