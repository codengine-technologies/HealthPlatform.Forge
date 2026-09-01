# -*- coding: utf-8 -*-
"""Aggregate the forge timing ledger (metrics/timings.jsonl).

Views
-----
--task {id}          per-step cost of one task (the `## Timings` table)
--task {id} --sync   idem, written back into the task file's ## Timings section
--last {N}           one line per task, the N most recent
--by-kind            global : how many builds / test suites / scans, and what
                     they cost (count, total, median, max) per step and kind.
                     This is the view that proves or disproves an optimisation.

Filters : --since YYYY-MM-DD, --step {name}, --repo {key}

Reporting is deliberately the only python in the instrumentation : the hot path
(measure.sh / step.sh) stays pure bash so a missing interpreter can never break
a build.
"""

import argparse
import glob
import io
import json
import os
import sys

KIND_COLS = ["build", "test", "scan", "lint", "capture", "restore", "nuget-wait"]


# --------------------------------------------------------------- utilities
def forge_root():
    d = os.path.abspath(os.getcwd())
    while True:
        if os.path.isfile(os.path.join(d, "CLAUDE.md")) and os.path.isdir(os.path.join(d, "tasks")):
            return d
        p = os.path.dirname(d)
        if p == d:
            break
        d = p
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def fmt_ms(ms):
    if ms is None:
        return "—"
    try:
        ms = int(ms)
    except (TypeError, ValueError):
        return "—"
    if ms < 0:
        return "—"
    if ms < 10000:
        return "%d.%d s" % (ms // 1000, (ms % 1000) // 100)
    s = ms // 1000
    m, s = s // 60, s % 60
    if m == 0:
        return "%d s" % s
    if m < 60:
        return "%d min %02d s" % (m, s)
    return "%d h %02d min" % (m // 60, m % 60)


def median(values):
    if not values:
        return None
    v = sorted(values)
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) // 2


def load(ledger, since=None, step=None, repo=None, task=None):
    events = []
    if not os.path.isfile(ledger):
        return events
    with io.open(ledger, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line or not line.startswith("{"):
                continue
            try:
                e = json.loads(line)
            except ValueError:
                continue  # a half-written line must never kill the report
            if since and e.get("ts", "") < since:
                continue
            if step and e.get("step") != step:
                continue
            if repo and e.get("repo") != repo:
                continue
            if task and e.get("task") != task:
                continue
            events.append(e)
    return events


def order_preserving_unique(seq):
    seen, out = set(), []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


# ------------------------------------------------------------ task view
def task_table(events, task_id):
    """Markdown table : one row per step, plus a cycle total."""
    steps = order_preserving_unique(
        [e.get("step", "-") for e in events if e.get("type") in ("step", "step_start", "cmd")]
    )

    lines = []
    lines.append("| Étape | Statut | Durée | Builds | Tests | Scans | Détail |")
    lines.append("|---|---|---|---|---|---|---|")

    tot_dur = 0
    tot = dict((k, [0, 0]) for k in KIND_COLS)  # kind -> [count, ms]
    any_step_dur = False

    for st in steps:
        st_events = [e for e in events if e.get("step") == st]
        closing = [e for e in st_events if e.get("type") == "step"]
        cmds = [e for e in st_events if e.get("type") == "cmd"]

        status = closing[-1].get("status", "?") if closing else "en cours"
        note = closing[-1].get("note", "") if closing else ""
        iters = closing[-1].get("iterations") if closing else None
        dur = closing[-1].get("duration_ms") if closing else None
        if dur:
            tot_dur += int(dur)
            any_step_dur = True

        per_kind = {}
        for c in cmds:
            k = c.get("kind", "other")
            d = c.get("duration_ms") or 0
            cnt, ms = per_kind.get(k, (0, 0))
            per_kind[k] = (cnt + 1, ms + int(d))
            if k in tot:
                tot[k][0] += 1
                tot[k][1] += int(d)

        def cell(kind):
            if kind not in per_kind:
                return "—"
            cnt, ms = per_kind[kind]
            return "%d (%s)" % (cnt, fmt_ms(ms))

        detail = []
        if iters:
            detail.append("%s itération(s)" % iters)
        repos = order_preserving_unique([c.get("repo", "-") for c in cmds if c.get("repo", "-") != "-"])
        for r in repos:
            rc = [c for c in cmds if c.get("repo") == r]
            b = len([c for c in rc if c.get("kind") == "build"])
            t = len([c for c in rc if c.get("kind") == "test"])
            if b or t:
                detail.append("%s %dB/%dT" % (r, b, t))
        for k in per_kind:
            if k not in KIND_COLS:
                cnt, ms = per_kind[k]
                detail.append("%s ×%d (%s)" % (k, cnt, fmt_ms(ms)))
        if note:
            detail.append(note)

        lines.append(
            "| /%s | %s | %s | %s | %s | %s | %s |"
            % (st, status, fmt_ms(dur), cell("build"), cell("test"), cell("scan"),
               ", ".join(detail) if detail else "—")
        )

    lines.append(
        "| **Total cycle** | | **%s** | **%d (%s)** | **%d (%s)** | **%d (%s)** | |"
        % (fmt_ms(tot_dur) if any_step_dur else "—",
           tot["build"][0], fmt_ms(tot["build"][1]),
           tot["test"][0], fmt_ms(tot["test"][1]),
           tot["scan"][0], fmt_ms(tot["scan"][1]))
    )

    extra = [(k, v) for k, v in tot.items() if k not in ("build", "test", "scan") and v[0]]
    if extra:
        lines.append("")
        lines.append(
            "Autres commandes mesurées : "
            + ", ".join("%s ×%d (%s)" % (k, v[0], fmt_ms(v[1])) for k, v in sorted(extra))
        )

    return "\n".join(lines)


def sync_task_file(root, task_id, table):
    """Replace (or append) the ## Timings section of the task file."""
    candidates = (
        glob.glob(os.path.join(root, "tasks", "wip-%s.md" % task_id))
        + glob.glob(os.path.join(root, "tasks", "review-%s.md" % task_id))
        + glob.glob(os.path.join(root, "tasks", "done-%s.md" % task_id))
        + glob.glob(os.path.join(root, "tasks", "todo-%s.md" % task_id))
        + glob.glob(os.path.join(root, "tasks", "archived", "archived-%s.md" % task_id))
    )
    if not candidates:
        return None
    path = candidates[0]

    with io.open(path, encoding="utf-8") as fh:
        content = fh.read()

    section = (
        "## Timings\n\n"
        "*(généré par `tools/timing/report.sh --task %s --sync` — ne pas éditer à la main)*\n\n"
        "%s\n" % (task_id, table)
    )

    marker = "\n## Timings"
    idx = content.find(marker)
    if idx == -1:
        if not content.endswith("\n"):
            content += "\n"
        content += "\n" + section
    else:
        rest = content[idx + 1:]
        nxt = rest.find("\n## ", 1)
        tail = rest[nxt + 1:] if nxt != -1 else ""
        content = content[: idx + 1] + section + (("\n" + tail) if tail else "")

    with io.open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(content)
    return path


# ------------------------------------------------------------- other views
def last_view(events, n):
    tasks = order_preserving_unique([e.get("task") for e in events if e.get("task") not in (None, "-")])
    tasks = tasks[-n:]
    out = ["| Task | Durée cycle | Builds | Tests | Scans | Étapes |", "|---|---|---|---|---|---|"]
    for t in tasks:
        te = [e for e in events if e.get("task") == t]
        dur = sum(int(e.get("duration_ms") or 0) for e in te if e.get("type") == "step")
        cmds = [e for e in te if e.get("type") == "cmd"]
        nb = lambda k: len([c for c in cmds if c.get("kind") == k])  # noqa: E731
        steps = order_preserving_unique([e.get("step") for e in te if e.get("type") == "step"])
        out.append("| %s | %s | %d | %d | %d | %s |"
                   % (t, fmt_ms(dur), nb("build"), nb("test"), nb("scan"),
                      " → ".join("/" + s for s in steps)))
    return "\n".join(out)


def by_kind_view(events):
    cmds = [e for e in events if e.get("type") == "cmd"]
    buckets = {}
    for c in cmds:
        key = (c.get("step", "-"), c.get("kind", "other"))
        buckets.setdefault(key, []).append(int(c.get("duration_ms") or 0))

    tasks = set(e.get("task") for e in events if e.get("task") not in (None, "-"))
    ntasks = max(1, len(tasks))

    out = ["| Étape | Kind | N | Par task | Total | Médiane | Max |", "|---|---|---|---|---|---|---|"]
    for (st, kind) in sorted(buckets):
        v = buckets[(st, kind)]
        out.append("| /%s | %s | %d | %.1f | %s | %s | %s |"
                   % (st, kind, len(v), len(v) / float(ntasks),
                      fmt_ms(sum(v)), fmt_ms(median(v)), fmt_ms(max(v))))

    grand = {}
    for (st, kind), v in buckets.items():
        grand.setdefault(kind, []).extend(v)
    out.append("")
    out.append("| Kind (toutes étapes) | N | Par task | Total | Médiane |")
    out.append("|---|---|---|---|---|")
    for kind in sorted(grand):
        v = grand[kind]
        out.append("| %s | %d | %.1f | %s | %s |"
                   % (kind, len(v), len(v) / float(ntasks), fmt_ms(sum(v)), fmt_ms(median(v))))
    out.append("")
    out.append("Base : %d task(s) instrumentée(s)." % len(tasks))
    return "\n".join(out)


# ------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Forge timing report")
    ap.add_argument("--task")
    ap.add_argument("--sync", action="store_true", help="write the ## Timings section into the task file")
    ap.add_argument("--last", type=int)
    ap.add_argument("--by-kind", action="store_true")
    ap.add_argument("--since")
    ap.add_argument("--step")
    ap.add_argument("--repo")
    args = ap.parse_args()

    # The Windows console defaults to cp1252 : accented output would either
    # mojibake or crash on characters like the arrow in the --last view.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    root = forge_root()
    ledger = os.path.join(root, "metrics", "timings.jsonl")

    if args.task:
        events = load(ledger, since=args.since, step=args.step, repo=args.repo, task=args.task)
        if not events:
            sys.stdout.write("Aucune mesure pour %s (ledger : %s)\n" % (args.task, ledger))
            return 0
        table = task_table(events, args.task)
        if args.sync:
            path = sync_task_file(root, args.task, table)
            sys.stdout.write("## Timings synchronisé dans %s\n" % (path or "(task file introuvable)"))
        else:
            sys.stdout.write("### Timings — %s\n\n%s\n" % (args.task, table))
        return 0

    events = load(ledger, since=args.since, step=args.step, repo=args.repo)
    if not events:
        sys.stdout.write("Ledger vide ou absent : %s\n" % ledger)
        return 0

    if args.by_kind:
        sys.stdout.write("### Coût par étape et par kind\n\n%s\n" % by_kind_view(events))
    else:
        sys.stdout.write("### Derniers cycles\n\n%s\n" % last_view(events, args.last or 10))
    return 0


if __name__ == "__main__":
    sys.exit(main())
