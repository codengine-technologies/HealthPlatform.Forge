"""Temps 1 : rejoue les formes SQL du tir 174846 sur une base de banc et sur la base de Virginie.

Même méthode que /loadtest-findings (explain_script : plan générique, paramètres tirés de la base et
jamais affichés, ROLLBACK). Le garde-fou BENCH_DB de findings.run_explain n'est pas modifié : la base
de Virginie (boîte de formation, données de test) est jouée par un appel psql direct, en lecture seule.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path("D:/TechWatch/HealthPlatform")
sys.path.insert(0, str(ROOT / "Tools" / "loadtest-findings"))
sys.path.insert(0, str(ROOT / "Api" / "Mail" / "tests" / "loadtest-k6"))
import findings  # noqa: E402
import report_postgres as rp  # noqa: E402

PGSTATS = ROOT / "Api/Mail/tests/loadtest-k6/reports/2026-11-08/pgstats-journey-174846.tsv"
DBS = {"banc": "u_l9l_b27c2b6f659b50f6240b3481927d0381", "virginie": "u_vmm_c9e6ca8101453ceff74a38098a6223c9"}
OUT = Path(__file__).parent

# Une page de liste = les 18 messages les plus récents de l'INBOX (18 lignes par appel au tir).
PAGE_MAILS = """(SELECT array_agg("Id") FROM (SELECT "Id" FROM "Mails" WHERE "FolderPath" = 'INBOX'
                 ORDER BY "SentDate" DESC NULLS LAST LIMIT 18) s)"""
PAGE_DOCS = """(SELECT coalesce(array_agg(d."Id"), '{}') FROM "MailMedicalDocuments" d WHERE d."MailId" IN (
                 SELECT "Id" FROM "Mails" WHERE "FolderPath" = 'INBOX' ORDER BY "SentDate" DESC NULLS LAST LIMIT 18))"""
TERMS = "'{%compte%,%rendu%,%synthese%}'"

FORMS = {
    # recherche plein texte : candidats = tous les contenus du dossier qui ont un corps
    "840774b6aad35df6f93d47d8d971aca0": ("recherche plein texte — contenus", "text[],uuid[],int,text,int",
        f"""SELECT {TERMS} AS p1, (SELECT array_agg(mc."Id") FROM "MailContents" mc JOIN "Mails" m ON m."Id" = mc."MailId"
            WHERE m."FolderPath" = 'INBOX' AND mc."Body" IS NOT NULL) AS p2, 200 AS p3, '\\' AS p4, 0 AS p5"""),
    "28e9d819261554f956f0ee69032938d7": ("recherche plein texte — documents", "text[],uuid[],int,text,int",
        f"""SELECT {TERMS} AS p1, (SELECT array_agg(d."Id") FROM "MailMedicalDocuments" d JOIN "Mails" m ON m."Id" = d."MailId"
            WHERE m."FolderPath" = 'INBOX' AND d."Body" IS NOT NULL) AS p2, 200 AS p3, '\\' AS p4, 0 AS p5"""),
    "bc5acb2c69c5d6799de85c3fd161a904": ("ouvrir un message — document", "uuid",
        """SELECT (SELECT "MailId" FROM "MailMedicalDocuments" ORDER BY "CreatedAt" DESC LIMIT 1) AS p1"""),
    "ac42e9c32aa51dc548795bf6a9692db0": ("page de liste — documents et comptages", "uuid[]",
        f"SELECT {PAGE_MAILS} AS p1"),
    "4c9c73a7b84af06ddf5fcf9b73b3c7ab": ("télécharger une pièce jointe", "uuid,text,int,int",
        """SELECT a."MailId" AS p1, a."FileName" AS p2, 0 AS p3, 1 AS p4 FROM "MailAttachments" a
           WHERE a."Content" IS NOT NULL AND a."DocumentId" IS NOT NULL ORDER BY a."Id" LIMIT 1"""),
    "9b0276b995554c73320b5caa00935e87": ("recherche vectorielle — documents (FND-010)", "vector,text,text,float8,int",
        """SELECT (SELECT "Embedding"::text FROM "MailContents" WHERE "Embedding" IS NOT NULL ORDER BY "Id" LIMIT 1) AS p1,
           'INBOX' AS p2, 'openai:text-embedding-3-small' AS p3, 0.9 AS p4, 20 AS p5"""),
    "90fed31c06a6aff57d1fb5c7c8d25a5d": ("recherche vectorielle — contenus", "vector,text,text,float8,int",
        """SELECT (SELECT "Embedding"::text FROM "MailContents" WHERE "Embedding" IS NOT NULL ORDER BY "Id" LIMIT 1) AS p1,
           'INBOX' AS p2, 'openai:text-embedding-3-small' AS p3, 0.9 AS p4, 20 AS p5"""),
    "2a6ce021d70dc17b91701c8f338e7a6f": ("ouvrir un message — contenu", "uuid",
        """SELECT (SELECT "MailId" FROM "MailContents" ORDER BY "Id" LIMIT 1) AS p1"""),
    "8f9a23fbdfe763775fed3766b575821b": ("doublons actifs d'une page", "uuid[],int,int,int,int",
        f"SELECT {PAGE_DOCS} AS p1, 1 AS p2, 1 AS p3, 2 AS p4, 3 AS p5"),
    "9ecf42a479e49a52787a30295de1f894": ("acquittements de biologie d'une page", "uuid[]",
        f"SELECT {PAGE_DOCS} AS p1"),
    "38927728f1f6554f6d1a7c88063a13be": ("messages d'une page, par UID", "text,int[],bigint",
        """SELECT 'INBOX' AS p1, (SELECT array_agg("Uid") FROM (SELECT "Uid" FROM "Mails" WHERE "FolderPath" = 'INBOX'
            ORDER BY "SentDate" DESC NULLS LAST LIMIT 18) s) AS p2,
           (SELECT max("UidValidity") FROM "Mails" WHERE "FolderPath" = 'INBOX') AS p3"""),
}
# FND-014 : 25 motifs '%<Message-ID>%' tirés des messages de la page (complétés si moins de 25)
FND014 = "a5978bf1120a527de14ca8d1c8283f21"
FORMS[FND014] = ("messages qui citent un fil (FND-014)", ",".join(["text"] * 25),
    "SELECT " + ", ".join(
        f"""(SELECT '%' || coalesce("MessageId", 'absent') || '%' FROM "Mails" WHERE "FolderPath" = 'INBOX'
             ORDER BY "SentDate" DESC NULLS LAST OFFSET {i - 1} LIMIT 1) AS p{i}""" for i in range(1, 26)))


def psql(db, script):
    cmd = ["docker", "exec", "-i", "postgres-pgvector", "psql", "-U", "postgres", "-d", db, "-X", "-q", "-A", "-t"]
    done = subprocess.run(cmd, input=script.encode("utf-8"), capture_output=True)
    out = done.stdout.decode("utf-8", "replace").replace("\r", "")
    if done.returncode != 0:
        raise RuntimeError(done.stderr.decode("utf-8", "replace").strip()[:500])
    return out


def measure(plan):
    """Temps d'exécution, pages du nœud racine (hit + read), lignes rendues."""
    exec_ms = float(re.search(r"Execution Time: ([\d.]+) ms", plan).group(1))
    buf = re.search(r"Buffers: shared ((?:hit=\d+)?\s*(?:read=\d+)?)", plan)
    pages = sum(int(x) for x in re.findall(r"=(\d+)", buf.group(1))) if buf else 0
    rows = re.search(r"actual time=[\d.]+\.\.[\d.]+ rows=(\d+)", plan)
    return exec_ms, pages, int(rows.group(1)) if rows else None


def main():
    rows = {r["queryid"]: r for r in rp.read_pgstats(PGSTATS.read_text(encoding="utf-8"))}
    results = []
    for form, (label, types, params_sql) in FORMS.items():
        sql = rows[form]["query"]
        script = findings.explain_script(sql, types.split(","), params_sql)
        entry = {"form": form, "label": label}
        for name, db in DBS.items():
            try:
                psql(db, script)  # chauffe du cache
                plan = psql(db, script)
                (OUT / f"{name}-{form}.txt").write_text(f"-- forme : {form}\n-- base : {db}\n{plan}", encoding="utf-8")
                entry[name] = measure(plan)
            except Exception as ex:  # noqa: BLE001
                entry[name] = None
                entry[name + "_error"] = str(ex)
        results.append(entry)
        print(json.dumps(entry, ensure_ascii=False))
    (OUT / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
