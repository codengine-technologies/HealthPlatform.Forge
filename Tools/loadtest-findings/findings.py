#!/usr/bin/env python
"""Findings de banc (task-433) : les candidats d'un tir, et le contrôle de non-confabulation.

Deux sous-commandes, au service du playbook `agents/loadtest-findings.md` :

    python Tools/loadtest-findings/findings.py candidates --pgstats {tsv} [--http-reqs N]
        [--registry Docs/audits/findings-registry.md] [--full] [--max 8] [--max-signaled 6]
    python Tools/loadtest-findings/findings.py check --section {rapport.md} --pgstats {tsv}
        --commit {sha} [--repo Api/Mail] [--plans {dossier}] [--registry {registre}]

`candidates` choisit les formes à explorer et rend, pour chacune, un dossier de preuves : les
mesures du tir déjà formatées (l'agent les recopie, il ne les recalcule pas), les détecteurs de
task-431, la route et le site de task-432, et le texte SQL complet.

`check` relit une section « Findings — analyse de code » et vérifie mécaniquement que :
- chaque mesure d'un finding est celle du `pgstats-*.tsv`, au caractère près ;
- chaque `fichier:ligne` existe au commit du tir ;
- chaque ligne de plan citée figure dans le plan sauvegardé du finding ;
- le registre n'a ni identifiant ni forme en double.

Codes de sortie : 0 conforme, 1 écart trouvé, 2 entrée illisible.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "Api" / "Mail" / "tests" / "loadtest-k6"
sys.path.insert(0, str(HARNESS))

PAGE_BYTES = 8192
GO = 1 << 30

# Statuts du registre qui dispensent de ré-explorer : la forme est seulement remesurée.
SETTLED = ("task", "corrigé", "écarté")
CLASS_OFF_DETECTORS = "hors-détecteur"
# Une récidive est un défaut de même NATURE qu'un défaut corrigé. Le poids dans le tir (D5) dit
# combien une forme coûte, pas pourquoi : il ne fonde pas une récidive.
RECIDIVE_CLASSES = ("pages-par-ligne", "colonne-volumineuse", "sous-requete-correlee", "appels-par-requete")
SKELETON_CHARS = 60


# ───────────────────────── mesures d'une forme ─────────────────────────

def _n(row, key):
    return row.get(key) or 0


def _fr_int(value):
    return f"{int(round(value)):,}".replace(",", " ")


def metrics(row, totals):
    """Les mesures d'une forme, formatées une fois pour toutes : le finding les recopie telles quelles."""
    calls = _n(row, "calls")
    rows = max(_n(row, "rows"), 1)
    pages = _n(row, "shared_hit") + _n(row, "shared_read")
    read = _n(row, "shared_read")
    total_ms = _n(row, "total_ms")
    time_share = total_ms / totals["total_ms"] * 100 if totals.get("total_ms") else 0
    disk_share = read / totals["shared_read"] * 100 if totals.get("shared_read") else 0
    return {
        "Appels": _fr_int(calls),
        "Temps SQL": f"{total_ms / 1000:.1f} s",
        "Part du temps SQL": f"{time_share:.1f} %",
        "ms par appel": f"{_n(row, 'mean_ms'):.2f}",
        "Lignes par appel": f"{_n(row, 'rows') / calls:.1f}" if calls else "0.0",
        "Pages lues": f"{pages * PAGE_BYTES / GO:.1f} Go",
        "Pages par ligne": f"{pages / rows:.1f}",
        "Pages par appel": f"{pages / calls:.0f}" if calls else "0",
        "Lu sur disque": f"{read * PAGE_BYTES / GO:.1f} Go",
        "Part des lectures disque": f"{disk_share:.1f} %",
        "Bases": _fr_int(_n(row, "bases")),
    }


def skeleton(query):
    """Deux formes au même début de texte sont une même requête en variantes : une seule exploration."""
    return re.sub(r"\s+", " ", query or "").strip()[:SKELETON_CHARS]


class _NoSignals:
    """Mode dégradé sans task-431 : aucun détecteur, les candidats viennent du seul coût."""

    @staticmethod
    def totals_of(rows):
        return {"total_ms": sum(_n(r, "total_ms") for r in rows),
                "shared_read": sum(_n(r, "shared_read") for r in rows)}

    @staticmethod
    def defect_signals(rows, http_reqs=None, totals=None):
        return []


def _signals():
    try:
        import report_signals
        return report_signals
    except ImportError:
        return _NoSignals


# ───────────────────────── registre ─────────────────────────

_REGISTRY_ROW = re.compile(r"^\|\s*(FND-\d{3})\s*\|([^|]*)\|(.*)$")
_MD5 = re.compile(r"\b[0-9a-f]{32}\b")


def read_registry(path):
    """Les lignes du registre : {id, forms, classe, statut}. Colonnes : id | formes | classe | titre |
    premier tir | verdict | statut | task | mesure après. Une ligne peut porter plusieurs formes : la
    forme du premier tir, ses variantes, la forme d'après correctif."""
    entries = []
    if not path or not Path(path).exists():
        return entries
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = _REGISTRY_ROW.match(line.strip())
        if not m:
            continue
        cells = [c.strip() for c in m.group(3).split("|")]
        entries.append({
            "id": m.group(1),
            "forms": _MD5.findall(m.group(2)),
            "classe": cells[0].strip("`") if cells else "",
            "statut": cells[4].lower() if len(cells) > 4 else "",
        })
    return entries


def _settled(entry):
    return any(entry["statut"].startswith(s) for s in SETTLED)


# ───────────────────────── candidats ─────────────────────────

def select(rows, http_reqs=None, registry=(), full=False, max_total=8, max_signaled=6):
    """
    Les formes à explorer, dans l'ordre : les formes signalées (task-431) par temps SQL décroissant,
    au plus `max_signaled`, puis les formes les plus coûteuses en temps, puis en pages lues, jusqu'à
    `max_total`. Une variante (même début de texte qu'un candidat) n'occupe pas de place.
    Sans `full`, une forme réglée au registre (task, corrigé, écarté) est seulement remesurée.
    """
    rs = _signals()

    totals = rs.totals_of(rows)
    signaled = {id(s["row"]): s["signals"] for s in rs.defect_signals(rows, http_reqs, totals)}
    by_form = {f: e for e in registry for f in e["forms"]}
    fixed_classes = {}
    for e in registry:
        if e["statut"].startswith("corrigé") and e["classe"] in RECIDIVE_CLASSES:
            fixed_classes.setdefault(e["classe"], []).append(e["id"])

    chosen, variants, skipped = [], {}, []
    seen = {}
    present = {r.get("queryid"): r for r in rows}
    # Chaque forme réglée du registre est remesurée, qu'elle soit encore là ou non : absente du tir,
    # son correctif tient ; présente, son coût se compare à celui du premier tir.
    remeasured = [] if full else [(e, next((present[f] for f in e["forms"] if f in present), None))
                                  for e in registry if e["forms"] and _settled(e)]

    def consider(row, pool_signaled):
        known = by_form.get(row.get("queryid"))
        if known and _settled(known) and not full:
            return False
        key = skeleton(row.get("query"))
        if key in seen:
            variants.setdefault(seen[key], []).append(row)
            return False
        if len(chosen) >= max_total or (pool_signaled and sum(1 for c in chosen if c["signals"]) >= max_signaled):
            if pool_signaled:
                skipped.append(row)
            return False
        sig = signaled.get(id(row), [])
        classes = [d for d, _ in sig] or [CLASS_OFF_DETECTORS]
        chosen.append({
            "row": row,
            "signals": sig,
            "known": known,
            "recidive": sorted({fid for c in classes for fid in fixed_classes.get(c, [])}),
            "metrics": metrics(row, totals),
        })
        seen[key] = row.get("queryid")
        return True

    for s in rs.defect_signals(rows, http_reqs, totals):
        consider(s["row"], True)
    rest = [r for r in rows if id(r) not in signaled]
    for ranking in ("total_ms", "pages"):
        key = (lambda r: _n(r, "total_ms")) if ranking == "total_ms" else (
            lambda r: _n(r, "shared_hit") + _n(r, "shared_read"))
        for row in sorted(rest, key=key, reverse=True):
            if len(chosen) >= max_total:
                break
            if row.get("queryid") in {c["row"].get("queryid") for c in chosen}:
                continue
            consider(row, False)
    return {"chosen": chosen, "variants": variants, "remeasured": remeasured,
            "skipped": skipped, "totals": totals}


def render_candidates(result):
    out = ["# Candidats", ""]
    for i, c in enumerate(result["chosen"], 1):
        row = c["row"]
        out.append(f"## Candidat {i} — forme `{row.get('queryid')}`")
        out.append("")
        out.append(f"- **Base échantillon** : `{row.get('sample_db')}`")
        sig = "; ".join(f"`{d}` — {t}" for d, t in c["signals"]) or f"`{CLASS_OFF_DETECTORS}` (coût seul)"
        out.append(f"- **Détecteurs** : {sig}")
        sites = row.get("call_sites") or []
        out.append("- **Émise par** : " + (", ".join(f"`{r}` → `{s}`" for r, s in sites)
                                          if sites else "— (tir antérieur à task-432 : mode dégradé)"))
        if c["known"]:
            out.append(f"- **Registre** : {c['known']['id']} ({c['known']['statut']})")
        if c["recidive"]:
            out.append(f"- **Récidive possible** : même classe que {', '.join(c['recidive'])} (corrigé)")
        for v in result["variants"].get(row.get("queryid"), []):
            out.append(f"- **Variante** : `{v.get('queryid')}` ({_n(v, 'total_ms') / 1000:.1f} s)")
        out.append("")
        out.append("| Mesure | Valeur |")
        out.append("|---|---|")
        out.extend(f"| {k} | {v} |" for k, v in c["metrics"].items())
        out.append("")
        out.append("```sql")
        out.append(row.get("query") or "")
        out.append("```")
        out.append("")
    if result["remeasured"]:
        out.append("## Connus du registre — remesurés, non ré-explorés")
        out.append("")
        for entry, row in result["remeasured"]:
            if row is None:
                out.append(f"- {entry['id']} ({entry['statut']}) : forme absente du tir")
                continue
            m = metrics(row, result["totals"])
            out.append(f"- {entry['id']} ({entry['statut']}) : {m['Temps SQL']}, {m['Part du temps SQL']} "
                       f"du temps, {m['Pages lues']} lus, {m['Lu sur disque']} sur disque")
        out.append("")
    if result["skipped"]:
        out.append("## Signalés non explorés (budget)")
        out.append("")
        out.extend(f"- `{r.get('queryid')}` — {_n(r, 'total_ms') / 1000:.1f} s — `{skeleton(r.get('query'))}…`"
                   for r in result["skipped"])
        out.append("")
    return "\n".join(out)


# ───────────────────────── contrôle de non-confabulation ─────────────────────────

_FINDING = re.compile(r"^####\s+(FND-\d{3}|FND-\?\?\?|Candidat[^\n]*)", re.MULTILINE)
_FORM = re.compile(r"\*\*Forme\*\*\s*:\s*`([0-9a-f]{32})`")
_METRIC_ROW = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$")
_FILE_LINE = re.compile(r"`((?:src|tests)/[^`\s:]+\.\w+):(\d+)`")
_PLAN_FILE = re.compile(r"\*\*Plan\*\*\s*:\s*`([^`]+)`")
_CODE_BLOCK = re.compile(r"```(?:text|plan)\n(.*?)```", re.DOTALL)


def _blocks(section):
    starts = [m.start() for m in _FINDING.finditer(section)] + [len(section)]
    return [section[a:b] for a, b in zip(starts, starts[1:])]


def _git_lines(repo, commit, path):
    try:
        text = subprocess.run(["git", "-C", str(repo), "show", f"{commit}:{path}"], capture_output=True,
                              check=True).stdout.decode("utf-8", "replace")
    except subprocess.CalledProcessError:
        return None
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def check(section, rows, commit, repo, plans_dir=None, registry_text=None):
    """Les écarts d'une section de findings à ses sources. Liste vide : conforme."""
    rs = _signals()

    totals = rs.totals_of(rows)
    by_form = {r.get("queryid"): r for r in rows}
    problems, checked = [], 0
    labels = set(metrics({}, totals).keys())
    for block in _blocks(section):
        title = block.splitlines()[0].strip("# ").strip()
        form = _FORM.search(block)
        if not form:
            problems.append(f"{title} : pas de `**Forme** : `md5``")
            continue
        row = by_form.get(form.group(1))
        if row is None:
            problems.append(f"{title} : forme {form.group(1)} absente du pgstats")
            continue
        expected = metrics(row, totals)
        for line in block.splitlines():
            m = _METRIC_ROW.match(line.strip())
            if not m or m.group(1) not in labels:
                continue
            checked += 1
            if m.group(2) != expected[m.group(1)]:
                problems.append(f"{title} : {m.group(1)} = {m.group(2)}, le pgstats dit {expected[m.group(1)]}")
        for path, line_no in _FILE_LINE.findall(block):
            checked += 1
            count = _git_lines(repo, commit, path)
            if count is None:
                problems.append(f"{title} : {path} absent au commit {commit}")
            elif int(line_no) > count:
                problems.append(f"{title} : {path}:{line_no} au-delà de la fin ({count} lignes) au commit {commit}")
        plan = _PLAN_FILE.search(block)
        quoted = _CODE_BLOCK.findall(block)
        if quoted and not plan:
            problems.append(f"{title} : plan cité sans fichier de plan (`**Plan** : `…``)")
        if plan and quoted:
            plan_path = Path(plans_dir or ".") / plan.group(1)
            if not plan_path.exists():
                problems.append(f"{title} : plan {plan.group(1)} introuvable")
            else:
                saved = plan_path.read_text(encoding="utf-8")
                for excerpt in quoted:
                    for qline in filter(None, (l.strip() for l in excerpt.splitlines())):
                        checked += 1
                        if qline != "…" and qline not in saved:
                            problems.append(f"{title} : ligne de plan absente du plan sauvegardé : {qline[:80]}")
    # Le tableau de synthèse : `| FND-NNN titre | verdict | classe | Temps SQL | Lu sur disque | gain |`.
    forms_of = {}
    for block in _blocks(section):
        ident = re.match(r"####\s+(FND-\d{3})", block)
        form = _FORM.search(block)
        if ident and form:
            forms_of[ident.group(1)] = form.group(1)
    for line in section.splitlines():
        m = re.match(r"^\|\s*(FND-\d{3})[^|]*\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|", line.strip())
        if not m or m.group(1) not in forms_of or forms_of[m.group(1)] not in by_form:
            continue
        expected = metrics(by_form[forms_of[m.group(1)]], totals)
        for label, cell in (("Temps SQL", m.group(4)), ("Lu sur disque", m.group(5))):
            checked += 1
            if cell.strip() != expected[label]:
                problems.append(f"synthèse {m.group(1)} : {label} = {cell.strip()}, le pgstats dit {expected[label]}")
    if registry_text is not None:
        ids, forms = {}, {}
        for line in registry_text.splitlines():
            m = _REGISTRY_ROW.match(line.strip())
            if not m:
                continue
            ids[m.group(1)] = ids.get(m.group(1), 0) + 1
            for f in _MD5.findall(m.group(2)):
                forms[f] = forms.get(f, 0) + 1
        problems += [f"registre : {k} en double" for k, n in {**ids, **forms}.items() if n > 1]
    return problems, checked


# ───────────────────────── plan d'exécution ─────────────────────────

# Les seules bases où un plan se joue : celles du banc, synthétiques. Jamais une base réelle.
BENCH_DB = re.compile(r"^(u_l\d+l_[0-9a-f]{32}|mss_registry_loadtest)$")


def explain_script(sql, types, params_sql, setup=()):
    """
    Le script psql d'un plan : paramètres tirés de la base par `params_sql` (jamais recopiés, le plan
    générique affiche `$1`), schéma éventuellement reconstitué par `setup`, le tout annulé par ROLLBACK.
    """
    names = [f"p{i}" for i in range(1, len(types) + 1)]
    lines = ["\\set ON_ERROR_STOP on", "BEGIN;", "SET LOCAL plan_cache_mode = force_generic_plan;"]
    lines += [f"{s.rstrip(';')};" for s in setup]
    if types:
        lines.append(f"{params_sql.rstrip(';')} \\gset")
        lines.append(f"PREPARE finding_q({', '.join(types)}) AS {sql.rstrip(';')};")
        args = ", ".join(f":'{n}'" for n in names)
        lines.append(f"EXPLAIN (ANALYZE, BUFFERS, COSTS OFF) EXECUTE finding_q({args});")
    else:
        lines.append(f"EXPLAIN (ANALYZE, BUFFERS, COSTS OFF) {sql.rstrip(';')};")
    lines.append("ROLLBACK;")
    return "\n".join(lines) + "\n"


def run_explain(db, script, container=None, user=None):
    if not BENCH_DB.match(db):
        raise ValueError(f"{db} n'est pas une base de banc : aucun plan n'y est joué")
    import os
    cmd = ["docker", "exec", "-i", container or os.environ.get("PG_CONTAINER", "postgres-pgvector"),
           "psql", "-U", user or os.environ.get("PG_USER", "postgres"), "-d", db, "-X", "-q", "-A", "-t"]
    done = subprocess.run(cmd, input=script.encode("utf-8"), capture_output=True)
    out = done.stdout.decode("utf-8", "replace").replace("\r", "")
    if done.returncode != 0:
        raise RuntimeError(done.stderr.decode("utf-8", "replace").strip() or out)
    return out


def column_sizes_script(table, columns):
    """
    Le poids moyen de chaque colonne d'une table, détoasté compris. Pourquoi : sous PostgreSQL 16,
    `EXPLAIN ANALYZE` n'envoie rien au client et ne lit donc PAS les valeurs TOAST. Le plan d'une
    forme qui charge un contenu volumineux montre 2 pages là où le tir en a lu 18 par appel : pour
    la classe `colonne-volumineuse`, la preuve est le poids de chaque colonne, pas le plan.
    """
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table) or not all(
            re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", c) for c in columns):
        raise ValueError("table et colonnes : identifiants simples seulement")
    cells = ", ".join(f'round(avg(pg_column_size("{c}")))::bigint AS "{c}"' for c in columns)
    return ("\\set ON_ERROR_STOP on\n"
            f'SELECT count(*) AS "lignes", {cells} FROM "{table}";\n')


# ───────────────────────── entrée ─────────────────────────

def _read_rows(path):
    import report_postgres as rp
    return rp.read_pgstats(Path(path).read_text(encoding="utf-8"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("candidates")
    c.add_argument("--pgstats", required=True)
    c.add_argument("--http-reqs", type=int)
    c.add_argument("--registry")
    c.add_argument("--full", action="store_true", help="ignorer le registre : tout ré-explorer")
    c.add_argument("--max", type=int, default=8)
    c.add_argument("--max-signaled", type=int, default=6)
    k = sub.add_parser("check")
    k.add_argument("--section", required=True)
    k.add_argument("--pgstats", required=True)
    k.add_argument("--commit", required=True)
    k.add_argument("--repo", default=str(ROOT / "Api" / "Mail"))
    k.add_argument("--plans")
    k.add_argument("--registry")
    e = sub.add_parser("explain")
    e.add_argument("--pgstats", required=True)
    e.add_argument("--form", required=True, help="md5 de la forme ; son texte SQL vient du pgstats")
    e.add_argument("--db", help="base de banc (défaut : sample_db de la forme)")
    e.add_argument("--types", default="", help="types des paramètres, séparés par des virgules : uuid,text[]")
    e.add_argument("--params-sql", default="", help="SELECT … AS p1, … AS p2 sur la base : valeurs jamais affichées")
    e.add_argument("--sql-file", help="variante à plan comparé (le correctif proposé), au lieu du texte du tir")
    e.add_argument("--setup", action="append", default=[],
                   help="reconstitution du schéma du commit du tir (ex. DROP INDEX …), annulée par ROLLBACK")
    e.add_argument("--out", required=True)
    z = sub.add_parser("column-sizes")
    z.add_argument("--db", required=True)
    z.add_argument("--table", required=True)
    z.add_argument("--columns", required=True, help="colonnes séparées par des virgules")
    z.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    if args.cmd == "column-sizes":
        cols = [c.strip() for c in args.columns.split(",") if c.strip()]
        try:
            script = column_sizes_script(args.table, cols)
            # Mode aligné : une table lisible, citée telle quelle dans le finding.
            out = run_explain(args.db, script).strip()
        except (ValueError, RuntimeError) as exc:
            print(f"mesure non jouée : {exc}", file=sys.stderr)
            return 2
        header = "| lignes | " + " | ".join(f"{c} (octets/ligne)" for c in cols) + " |"
        body = "| " + " | ".join(out.split("|")) + " |"
        text = f"-- base : {args.db}\n-- table : {args.table}\n{header}\n{body}\n"
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
        sys.stdout.write(text)
        return 0

    try:
        rows = _read_rows(args.pgstats)
    except OSError as exc:
        print(f"pgstats illisible : {exc}", file=sys.stderr)
        return 2
    if not rows:
        print("pgstats vide ou illisible", file=sys.stderr)
        return 2

    if args.cmd == "candidates":
        result = select(rows, args.http_reqs, read_registry(args.registry), args.full, args.max, args.max_signaled)
        sys.stdout.write(render_candidates(result) + "\n")
        return 0

    if args.cmd == "explain":
        row = next((r for r in rows if r.get("queryid") == args.form), None)
        if row is None:
            print(f"forme {args.form} absente du pgstats", file=sys.stderr)
            return 2
        sql = Path(args.sql_file).read_text(encoding="utf-8") if args.sql_file else row.get("query")
        types = [t.strip() for t in args.types.split(",") if t.strip()]
        db = args.db or row.get("sample_db")
        try:
            plan = run_explain(db, explain_script(sql, types, args.params_sql, args.setup))
        except (ValueError, RuntimeError) as exc:
            print(f"plan non joué : {exc}", file=sys.stderr)
            return 2
        head = [f"-- forme : {args.form}", f"-- base : {db}",
                f"-- requête : {'variante ' + Path(args.sql_file).name if args.sql_file else 'texte du tir'}"]
        head += [f"-- schéma reconstitué : {s}" for s in args.setup]
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text("\n".join(head) + "\n" + plan, encoding="utf-8")
        sys.stdout.write(plan)
        return 0

    section = Path(args.section).read_text(encoding="utf-8")
    start = section.find("## Findings — analyse de code")
    if start < 0:
        print("section « Findings — analyse de code » absente", file=sys.stderr)
        return 2
    end = section.find("\n## ", start + 5)
    registry = Path(args.registry).read_text(encoding="utf-8") if args.registry else None
    problems, checked = check(section[start:end if end > 0 else None], rows, args.commit, args.repo,
                              args.plans, registry)
    for p in problems:
        print(f"✗ {p}")
    print(f"{checked} élément(s) contrôlé(s), {len(problems)} écart(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
