"""task-439 — coût de la nouvelle recherche plein texte, sur une copie de la boîte de formation (11 178 mails).

Rejoue, en EXPLAIN ANALYZE, la forme que compose SemanticSearchRepository.FindFullTextMatchesAsync : la sous-requête
de SearchTextSchema.MatchesSql (colonnes "SearchText" indexées, ou normalisation à la volée) jointe aux mails du
dossier, triée, bornée. Les termes sont ceux de la campagne du 2026-11-09, normalisés comme SearchTerms.Parse.
Jamais sur la base de Virginie elle-même : sur une copie (CREATE DATABASE … TEMPLATE …), provisionnée.

Usage : python replay_task439.py <base-copie> [--fallback]
"""
import json
import statistics
import subprocess
import sys

DB = sys.argv[1]
INDEXED = "--fallback" not in sys.argv
SOURCES = [  # table, colonne de mail, expression, document médical
    ("Mails", "Id", """coalesce(x."Subject", '') || ' ' || coalesce(x."FromName", '') || ' ' || coalesce(x."FromAddress", '')""", False),
    ("MailContents", "MailId", 'x."Body"', False),
    ("MailAttachments", "MailId", 'x."FileName"', False),
    ("MailMedicalDocuments", "MailId", 'x."Body"', True),
]
QUERIES = [["hemoglobine"], ["urgent"], ["cholesterol"], ["catherine", "bernard"],
           ["bilan", "lipidique", "cholesterol", "total"], ["compte", "rendu", "synthese"]]


def matches_sql(kind, patterns):
    arr = "ARRAY[" + ",".join(f"'%{p}%'" for p in patterns) + "]::text[]"
    branches = []
    for table, mail_col, expr, is_doc in SOURCES:
        if kind != "both" and is_doc != (kind == "documents"):
            continue
        text = 'x."SearchText"' if INDEXED else f"public.search_normalize({expr})"
        branches.append(f"""SELECT t.i, x."{mail_col}" AS mail_id FROM unnest({arr}) WITH ORDINALITY AS t(p, i)
            INNER JOIN "{table}" AS x ON {text} LIKE t.p""")
    inner = f"""SELECT h.mail_id AS "MailId", count(DISTINCT h.i)::int AS "MatchedTerms"
        FROM ({' UNION ALL '.join(branches)}) AS h GROUP BY h.mail_id"""
    return f"""EXPLAIN (ANALYZE, TIMING OFF, SUMMARY ON)
        SELECT m."Id", m."Uid", m."FolderPath", t."MatchedTerms" FROM ({inner}) AS t
        INNER JOIN "Mails" AS m ON t."MailId" = m."Id" WHERE m."FolderPath" = 'INBOX'
        ORDER BY t."MatchedTerms" DESC, m."SentDate" IS NULL, m."SentDate" DESC, m."Uid" DESC LIMIT 25001;"""


def run(sql):
    out = subprocess.run(["docker", "exec", "-i", "postgres-pgvector", "psql", "-U", "postgres", "-d", DB, "-At"],
                         input=sql.encode(), capture_output=True).stdout.decode()
    rows = next((l for l in out.splitlines() if l.startswith("Limit") or "rows=" in l), "")
    ms = float(next(l for l in out.splitlines() if l.startswith("Execution Time")).split()[2])
    actual = rows.split("actual rows=")[1].split()[0] if "actual rows=" in rows else "?"
    return ms, actual


results = []
for kind in ["contents", "documents", "both"]:
    for q in QUERIES:
        times, rows = [], "?"
        for _ in range(6):
            ms, rows = run(matches_sql(kind, q))
            times.append(ms)
        med = statistics.median(times[1:])  # le premier passage chauffe le cache
        results.append({"kind": kind, "terms": q, "median_ms": round(med, 2), "rows": rows})
        print(f"{kind:9} {' '.join(q):40} {med:8.2f} ms  {rows:>5} lignes")
json.dump({"db": DB, "indexed": INDEXED, "results": results},
          open(f"results-{'indexed' if INDEXED else 'fallback'}.json", "w"), indent=1)
