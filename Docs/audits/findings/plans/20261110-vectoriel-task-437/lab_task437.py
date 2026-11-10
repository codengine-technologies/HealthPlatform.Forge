"""task-437 — index vectoriel HNSW : rappel, coût et taille, sur une copie de la boîte de formation (11 178 mails).

Jamais sur la base de Virginie elle-même : sur une copie (CREATE DATABASE … TEMPLATE …). Les phrases sont de vraies
phrases de recherche (phrases.json), nettoyées par SearchQueryHelper.BuildCleanedQuery (phrases-cleaned.tsv) puis
vectorisées par text-embedding-3-small comme en production (query-vectors.json).

La forme rejouée est celle de SemanticSearchRepository (task-437) : les candidats du modèle actif, du dossier, triés
sur l'expression indexée ("Embedding"::<type>(1536)) <=> requête, bornés ; le seuil de distance s'applique ensuite.

Usage (depuis la racine du plan de contrôle) :
  python lab_task437.py embed                       # vecteurs des phrases (clé : OPENAI_API_KEY ou Api/Mail/.env)
  python lab_task437.py exact   <base>              # vérité : top 10 exact par table (balayage complet)
  python lab_task437.py build   <base> vector|halfvec
  python lab_task437.py measure <base> vector|halfvec|none <ef_search> [limit]
  python lab_task437.py drop    <base>
"""
import base64
import json
import os
import statistics
import struct
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]  # racine du plan de contrôle
VECTORS = HERE / "query-vectors.json"
TRUTH = HERE / "exact-top10.json"
MODEL = "openai:text-embedding-3-small"
TABLES = {"contents": "MailContents", "documents": "MailMedicalDocuments"}
FOLDER = "INBOX"
FOLDER_FILTER = os.environ.get("LAB_FOLDER_FILTER", "")
RUNS = 5


def psql(db, sql):
    started = time.perf_counter()
    out = subprocess.run(["docker", "exec", "-i", "postgres-pgvector", "psql", "-U", "postgres", "-d", db, "-At",
                          "-v", "ON_ERROR_STOP=1", "-f", "-"], input=sql, capture_output=True, text=True,
                         encoding="utf-8", check=True).stdout
    return out, (time.perf_counter() - started) * 1000


def cleaned_phrases():
    rows = (HERE / "phrases-cleaned.tsv").read_text(encoding="utf-8").splitlines()
    return [tuple(r.split("\t")) for r in rows if r]


def vector_literal(values):
    return "[" + ",".join(f"{v:.8f}" for v in values) + "]"


def load_vectors():
    data = json.loads(VECTORS.read_text(encoding="utf-8"))
    out = {}
    for text, packed in data.items():
        raw = base64.b64decode(packed)
        out[text] = list(struct.unpack(f"<{len(raw) // 4}f", raw))
    return out


def embed():
    secret = os.environ.get("OPENAI_API_KEY", "").strip()
    if not secret:
        for line in (ROOT / "Api" / "Mail" / ".env").read_text(encoding="utf-8").splitlines():
            if line.startswith("OpenAi__ApiKey="):
                secret = line.split("=", 1)[1].strip().strip('"').strip("'")
    texts = [c for _, c in cleaned_phrases()]
    body = json.dumps({"model": "text-embedding-3-small", "input": texts}).encode("utf-8")
    request = urllib.request.Request("https://api.openai.com/v1/embeddings", data=body, method="POST",
                                     headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as response:
        data = sorted(json.loads(response.read().decode("utf-8"))["data"], key=lambda d: d["index"])
    store = {t: base64.b64encode(struct.pack(f"<{len(d['embedding'])}f", *d["embedding"])).decode("ascii")
             for t, d in zip(texts, data)}
    VECTORS.write_text(json.dumps(store, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(store)} vecteurs écrits")


def candidates_sql(table, kind, q, limit, seqscan=True):
    """La forme de production : les candidats bornés par l'index, puis retriés (relaxed_order rend un ordre approché)."""
    outer_folder = (f"""INNER JOIN "Mails" AS m ON m."Id" = c."MailId" AND m."FolderPath" = '{FOLDER}' """
                    if os.environ.get("LAB_OUTER_FOLDER") == "1" else "")
    return f"""SELECT c."MailId", c.distance FROM ({inner_sql(table, kind, q, limit)}) AS c {outer_folder}ORDER BY c.distance"""


def inner_sql(table, kind, q, limit):
    typed = f"""(x."Embedding"::{kind}(1536))""" if kind != "none" else 'x."Embedding"'
    qcast = f"'{q}'::{kind}(1536)" if kind != "none" else f"'{q}'::vector"
    # task-437 : comme VectorIndexSchema.CandidatesSql — distance exacte (pleine précision), tri sur l'expression indexée.
    distance = (f"{typed} <=> {qcast}" if os.environ.get("LAB_TYPED_DISTANCE") == "1"
                else f"""x."Embedding" <=> '{q}'::vector""")
    return f"""SELECT x."MailId", {distance} AS distance FROM "{table}" AS x
        WHERE x."EmbeddingModel" = '{MODEL}' AND x."Embedding" IS NOT NULL
          {FOLDER_FILTER}
        ORDER BY {typed} <=> {qcast} LIMIT {limit}"""


def exact(db):
    vectors = load_vectors()
    truth = {}
    for _, cleaned in cleaned_phrases():
        q = vector_literal(vectors[cleaned])
        for key, table in TABLES.items():
            out, _ = psql(db, f"SET enable_indexscan = off; {inner_sql(table, 'none', q, 10)};")
            truth[f"{key}|{cleaned}"] = [line.split("|")[0] for line in out.splitlines() if "|" in line]
    TRUTH.write_text(json.dumps(truth, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"vérité écrite : {len(truth)} listes")


def index_sql(table, kind):
    ops = "vector_cosine_ops" if kind == "vector" else "halfvec_cosine_ops"
    return (f"""CREATE INDEX "IX_LAB_{table}_{kind}" ON "{table}" USING hnsw (("Embedding"::{kind}(1536)) {ops}) """
            f"""WITH (m = 24, ef_construction = 200) WHERE "EmbeddingModel" = '{MODEL}'""")


def build(db, kind):
    for table in TABLES.values():
        _, ms = psql(db, f"SET maintenance_work_mem = '256MB'; {index_sql(table, kind)};")
        size, _ = psql(db, f"""SELECT pg_size_pretty(pg_relation_size('"IX_LAB_{table}_{kind}"'));""")
        print(f"{table:22} {kind:8} construction {ms:8.0f} ms   taille {size.strip()}")


def drop(db):
    for table in TABLES.values():
        for kind in ("vector", "halfvec"):
            psql(db, f'DROP INDEX IF EXISTS "IX_LAB_{table}_{kind}";')
    print("index du laboratoire supprimés")


def measure(db, kind, ef, limit, extra=""):
    vectors = load_vectors()
    truth = json.loads(TRUTH.read_text(encoding="utf-8"))
    report = {}
    for key, table in TABLES.items():
        recalls, times, pages, plans = [], [], [], set()
        for _, cleaned in cleaned_phrases():
            q = vector_literal(vectors[cleaned])
            settings = (f"SET hnsw.iterative_scan = relaxed_order; SET hnsw.ef_search = {ef};" if kind != "none" else "") + extra
            sql = candidates_sql(table, kind, q, limit)
            out, _ = psql(db, f"{settings} {sql};")
            got = [line.split("|")[0] for line in out.splitlines() if "|" in line][:10]
            expected = truth[f"{key}|{cleaned}"]
            recalls.append(len(set(got) & set(expected)) / max(len(expected), 1))
            explain = f"{settings} EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql};"
            run_ms, run_pages = [], []
            for _ in range(RUNS):
                out, _ = psql(db, explain)
                plan = json.loads(out[out.index("["):])[0]
                run_ms.append(plan["Execution Time"])
                node = plan["Plan"]
                run_pages.append(node.get("Shared Hit Blocks", 0) + node.get("Shared Read Blocks", 0))
                plans.add(scan_kind(node))
            times.append(statistics.median(run_ms))
            pages.append(statistics.median(run_pages))
        report[key] = {
            "rappel@10": round(statistics.mean(recalls), 4),
            "rappel@10 min": round(min(recalls), 2),
            "ms médiane": round(statistics.median(times), 2),
            "ms max": round(max(times), 2),
            "pages médiane": statistics.median(pages),
            "plans": sorted(plans),
        }
        print(f"{table:22} {kind:8} ef={ef:<4} limit={limit:<4} rappel@10 {report[key]['rappel@10']:.1%} "
              f"(min {report[key]['rappel@10 min']:.0%})  {report[key]['ms médiane']:7.2f} ms méd. "
              f"(max {report[key]['ms max']:.2f})  {report[key]['pages médiane']:.0f} pages  {sorted(plans)}")
    (HERE / f"results-{kind}-ef{ef}-limit{limit}.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def scan_kind(node):
    kinds = []
    stack = [node]
    while stack:
        n = stack.pop()
        if "Scan" in n["Node Type"]:
            kinds.append(f"{n['Node Type']}:{n.get('Relation Name', n.get('Index Name', ''))}")
        stack.extend(n.get("Plans", []))
    return ",".join(sorted(set(kinds)))


if __name__ == "__main__":
    command = sys.argv[1]
    if command == "embed":
        embed()
    elif command == "exact":
        exact(sys.argv[2])
    elif command == "build":
        build(sys.argv[2], sys.argv[3])
    elif command == "drop":
        drop(sys.argv[2])
    elif command == "measure":
        measure(sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]) if len(sys.argv) > 5 else 100,
                " ".join(sys.argv[6:]))
