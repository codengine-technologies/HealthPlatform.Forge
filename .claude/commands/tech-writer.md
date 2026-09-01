---
description: Rafraîchit la documentation vivante d'un EPIC depuis ses task files
argument-hint: "E{NNN} [--refresh]"
# ⚠️ MESURÉ le 2026-08-10, et à connaître avant de compter sur ce champ : `model`
# est bien analysé par le harnais (cette description-ci apparaît dans la liste des
# skills, preuve que le frontmatter est lu), mais il n'a AUCUN EFFET quand la
# commande est appelée par la chaîne via l'outil `Skill` — les instructions sont
# injectées dans le tour en cours, et le modèle courant continue. Contrôle : quatre
# messages assistant après l'invocation, tous en `claude-opus-5` dans le transcript
# de session, alors que ce champ demandait `sonnet`.
#
# Il ne sert donc qu'à une invocation MANUELLE (`/tech-writer E015` tapé par
# l'humain) — cas non éprouvé à ce jour. Pour que l'économie porte aussi sur la
# chaîne autonome, il faut faire du tech-writer un SOUS-AGENT
# (`.claude/agents/tech-writer.md` avec `model:`), que l'outil `Agent` lance dans
# son propre tour : là, le modèle s'applique sans ambiguïté.
model: sonnet
---

# /tech-writer — Maintain the living EPIC documentation

Read `agents/technical-writer.md` and act as the Technical Writer.

## ⏱️ Instrumentation (obligatoire)

Aucune commande coûteuse ici (lecture de task files, écriture de deux
markdowns), mais l'étape se borne quand même — c'est ce qui chiffrera le gain
d'un appel unique par EPIC en fin de run `/forge` au lieu d'un appel par task :

```bash
Tools/timing/step.sh start --task {task-id} --step tech-writer
Tools/timing/step.sh end --task {task-id} --step tech-writer --status ok
```

Invocation manuelle sans task en vol : `--task -`.

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
