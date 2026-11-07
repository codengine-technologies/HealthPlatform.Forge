"""Tests de Tools/loadtest-findings/findings.py (task-433). `python -m unittest Tools/loadtest-findings/test_findings.py`"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import findings as f  # noqa: E402

GO_PAGES = (1 << 30) // 8192


def row(form, query, total_ms, calls=1000, rows=1000, hit=0, read=0, bases=10, mean_ms=None):
    return {"queryid": form, "query": query, "total_ms": total_ms, "calls": calls, "rows": rows,
            "shared_hit": hit, "shared_read": read, "bases": bases, "sample_db": "u_l1l_" + "0" * 32,
            "mean_ms": mean_ms if mean_ms is not None else total_ms / calls, "call_sites": []}


# Une forme qui charge un contenu volumineux (D2), une qui lit trop de pages par ligne (D1),
# une coûteuse sans signal, une petite sans signal.
HEAVY = row("a" * 32, 'SELECT m."Id", m."Content" FROM "MailAttachments" AS m WHERE m."MailId" = $1',
            9000, rows=1000, hit=2 * GO_PAGES)
PAGES = row("b" * 32, 'SELECT t."Id", (SELECT count(*)::int FROM "MailTags" AS x WHERE x."TagId" = t."Id") FROM "Tags" AS t',
            8000, calls=1000, rows=1000, hit=2 * GO_PAGES)
COSTLY = row("c" * 32, 'SELECT s.id FROM mss_accounts AS s WHERE s.account_id = $1', 7000, hit=10_000)
SMALL = row("d" * 32, 'SELECT 1', 10)
ROWS = [HEAVY, PAGES, COSTLY, SMALL]


class MetricsTests(unittest.TestCase):
    def test_metrics_AreFormattedOnce_FromThePgstatsRow(self):
        totals = {"total_ms": 20_000, "shared_read": 0}
        m = f.metrics(row("e" * 32, "SELECT 1", 12_345.6, calls=4321, rows=8642, hit=GO_PAGES, bases=1885), totals)
        self.assertEqual(m["Appels"], "4 321")
        self.assertEqual(m["Temps SQL"], "12.3 s")
        self.assertEqual(m["Part du temps SQL"], "61.7 %")
        self.assertEqual(m["Lignes par appel"], "2.0")
        self.assertEqual(m["Pages lues"], "1.0 Go")
        self.assertEqual(m["Bases"], "1 885")

    def test_skeleton_GroupsVariants_OnTheirFirstCharacters(self):
        self.assertEqual(f.skeleton("SELECT  a,\n b FROM x"), "SELECT a, b FROM x")


class SelectTests(unittest.TestCase):
    def test_select_TakesSignaledFormsFirst_ThenTheCostliest(self):
        result = f.select(ROWS, max_total=3)
        self.assertEqual([c["row"]["queryid"] for c in result["chosen"]], ["a" * 32, "b" * 32, "c" * 32])
        self.assertIn("colonne-volumineuse", [d for d, _ in result["chosen"][0]["signals"]])
        self.assertIn("pages-par-ligne", [d for d, _ in result["chosen"][1]["signals"]])

    def test_select_CapsSignaledForms_AndListsTheRestAsSkipped(self):
        result = f.select(ROWS, max_total=8, max_signaled=1)
        self.assertEqual(result["chosen"][0]["row"]["queryid"], "a" * 32)
        self.assertIn(PAGES, result["skipped"])
        self.assertNotIn("b" * 32, [c["row"]["queryid"] for c in result["chosen"]])

    def test_select_AVariant_TakesNoSlot(self):
        variant = row("f" * 32, HEAVY["query"] + " ORDER BY m.\"Id\"", 50, hit=2 * GO_PAGES)
        result = f.select(ROWS + [variant], max_total=8)
        self.assertEqual(result["variants"]["a" * 32], [variant])
        self.assertNotIn("f" * 32, [c["row"]["queryid"] for c in result["chosen"]])

    def test_select_ASettledFinding_IsRemeasured_NotExplored(self):
        registry = [{"id": "FND-001", "forms": ["c" * 32], "classe": "hors-détecteur", "statut": "écarté"}]
        result = f.select(ROWS, registry=registry)
        self.assertNotIn("c" * 32, [c["row"]["queryid"] for c in result["chosen"]])
        self.assertEqual(result["remeasured"], [(registry[0], COSTLY)])

    def test_select_AFixedFormAbsentFromTheTir_IsRemeasuredAsAbsent(self):
        registry = [{"id": "FND-002", "forms": ["9" * 32], "classe": "colonne-volumineuse",
                     "statut": "corrigé et mesuré"}]
        result = f.select(ROWS, registry=registry)
        self.assertEqual(result["remeasured"], [(registry[0], None)])
        self.assertIn("forme absente du tir", f.render_candidates(result))

    def test_select_Full_IgnoresTheRegistry(self):
        registry = [{"id": "FND-001", "forms": ["c" * 32], "classe": "hors-détecteur", "statut": "écarté"}]
        result = f.select(ROWS, registry=registry, full=True)
        self.assertIn("c" * 32, [c["row"]["queryid"] for c in result["chosen"]])
        self.assertEqual(result["remeasured"], [])

    def test_select_AnOpenFinding_IsExploredAgain(self):
        registry = [{"id": "FND-003", "forms": ["c" * 32], "classe": "hors-détecteur", "statut": "ouvert"}]
        result = f.select(ROWS, registry=registry)
        chosen = {c["row"]["queryid"]: c for c in result["chosen"]}
        self.assertEqual(chosen["c" * 32]["known"]["id"], "FND-003")

    def test_select_SameDefectClassAsAFixedFinding_IsARecidive(self):
        registry = [{"id": "FND-003", "forms": ["9" * 32], "classe": "colonne-volumineuse",
                     "statut": "corrigé et mesuré"}]
        chosen = {c["row"]["queryid"]: c for c in f.select(ROWS, registry=registry)["chosen"]}
        self.assertEqual(chosen["a" * 32]["recidive"], ["FND-003"])
        self.assertEqual(chosen["c" * 32]["recidive"], [])

    def test_select_WithoutTheDetectors_RanksByCostAlone(self):
        with mock.patch.object(f, "_signals", return_value=f._NoSignals):
            result = f.select(ROWS, max_total=2)
        self.assertEqual([c["row"]["queryid"] for c in result["chosen"]], ["a" * 32, "b" * 32])
        self.assertTrue(all(c["signals"] == [] for c in result["chosen"]))

    def test_select_TheWeightInTheTir_NeverFoundsARecidive(self):
        registry = [{"id": "FND-002", "forms": ["9" * 32], "classe": "poids-dans-le-tir",
                     "statut": "corrigé et mesuré"}]
        chosen = f.select(ROWS, registry=registry)["chosen"]
        self.assertTrue(all(c["recidive"] == [] for c in chosen))


REGISTRY = """| Id | Formes | Classe | Titre | Premier tir | Verdict | Statut | Task | Mesure après |
|---|---|---|---|---|---|---|---|---|
| FND-001 | `{a}` `{b}` | `colonne-volumineuse` | x | 2026-11-06 | confirmé | corrigé et mesuré | task-429 | −60 % |
| FND-002 | `{c}` | `hors-détecteur` | y | 2026-11-06 | écarté | écarté | — | — |
"""


class RegistryTests(unittest.TestCase):
    def test_readRegistry_ReadsEveryFormOfARow_AndItsStatus(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "r.md"
            p.write_text(REGISTRY.format(a="a" * 32, b="b" * 32, c="c" * 32), encoding="utf-8")
            entries = f.read_registry(p)
        self.assertEqual([e["id"] for e in entries], ["FND-001", "FND-002"])
        self.assertEqual(entries[0]["forms"], ["a" * 32, "b" * 32])
        self.assertEqual(entries[0]["classe"], "colonne-volumineuse")
        self.assertEqual(entries[0]["statut"], "corrigé et mesuré")

    def test_readRegistry_AMissingFile_IsEmpty(self):
        self.assertEqual(f.read_registry("nowhere.md"), [])


def section(value="9.0 s", line="12", plan_line="Seq Scan on x", synth="9.0 s"):
    return f"""## Findings — analyse de code

| Finding | Verdict | Classe | Temps SQL | Lu sur disque | Gain borné |
|---|---|---|---|---|---|
| FND-001 Titre | confirmé | `colonne-volumineuse` | {synth} | 0.0 Go | x |

#### FND-001 — Titre

- **Forme** : `{"a" * 32}`
- **Site** : `src/Repo.cs:{line}`

| Mesure | Valeur |
|---|---|
| Temps SQL | {value} |
| Appels | 1 000 |

**Plan** : `FND-001.txt`

```text
{plan_line}
```
"""


class CheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        Path(self.tmp.name, "FND-001.txt").write_text("-- forme\nSeq Scan on x\n  Filter: y\n", encoding="utf-8")
        self.lines = mock.patch.object(f, "_git_lines", return_value=40)
        self.lines.start()

    def tearDown(self):
        self.lines.stop()
        self.tmp.cleanup()

    def run_check(self, text, registry=None):
        return f.check(text, ROWS, "abc1234", ".", self.tmp.name, registry)

    def test_check_AConformingSection_HasNoProblem(self):
        problems, checked = self.run_check(section())
        self.assertEqual(problems, [])
        self.assertGreaterEqual(checked, 6)

    def test_check_AMeasureThatIsNotThePgstats_IsReported(self):
        problems, _ = self.run_check(section(value="8.0 s"))
        self.assertEqual(len(problems), 1)
        self.assertIn("le pgstats dit 9.0 s", problems[0])

    def test_check_TheSummaryTable_IsCheckedToo(self):
        problems, _ = self.run_check(section(synth="7.0 s"))
        self.assertEqual(len(problems), 1)
        self.assertIn("synthèse FND-001", problems[0])

    def test_check_ALineBeyondTheFileAtTheTirCommit_IsReported(self):
        problems, _ = self.run_check(section(line="41"))
        self.assertIn("au-delà de la fin", problems[0])

    def test_check_AFileAbsentAtTheTirCommit_IsReported(self):
        with mock.patch.object(f, "_git_lines", return_value=None):
            problems, _ = self.run_check(section())
        self.assertIn("absent au commit abc1234", problems[0])

    def test_check_APlanLineNotInTheSavedPlan_IsReported(self):
        problems, _ = self.run_check(section(plan_line="Index Scan on x"))
        self.assertIn("ligne de plan absente", problems[0])

    def test_check_AFormAbsentFromThePgstats_IsReported(self):
        problems, _ = self.run_check(section().replace("a" * 32, "e" * 32))
        self.assertTrue(any("absente du pgstats" in p for p in problems))

    def test_check_ADuplicateInTheRegistry_IsReported(self):
        registry = REGISTRY.format(a="a" * 32, b="b" * 32, c="a" * 32)
        problems, _ = self.run_check(section(), registry)
        self.assertEqual(problems, [f"registre : {'a' * 32} en double"])


class ExplainTests(unittest.TestCase):
    def test_explainScript_RollsBack_UsesAGenericPlan_AndNeverPrintsTheParameters(self):
        script = f.explain_script('SELECT * FROM t WHERE id = $1', ["uuid"], 'SELECT id AS p1 FROM t LIMIT 1',
                                  ['DROP INDEX "IX_t"'])
        lines = script.splitlines()
        self.assertEqual(lines[1], "BEGIN;")
        self.assertEqual(lines[-1], "ROLLBACK;")
        self.assertIn("SET LOCAL plan_cache_mode = force_generic_plan;", lines)
        self.assertIn('DROP INDEX "IX_t";', lines)
        self.assertIn("SELECT id AS p1 FROM t LIMIT 1 \\gset", lines)
        self.assertIn("EXPLAIN (ANALYZE, BUFFERS, COSTS OFF) EXECUTE finding_q(:'p1');", lines)

    def test_runExplain_RefusesAnyBaseThatIsNotABenchBase(self):
        for db in ("postgres", "mss_registry", "u_prod_" + "0" * 32, "u_l1l_abc"):
            with self.assertRaises(ValueError, msg=db):
                f.run_explain(db, "SELECT 1;")

    def test_columnSizesScript_AcceptsOnlySimpleIdentifiers(self):
        self.assertIn('avg(pg_column_size("Content"))', f.column_sizes_script("MailAttachments", ["Content"]))
        with self.assertRaises(ValueError):
            f.column_sizes_script('t"; DROP TABLE x; --', ["c"])


if __name__ == "__main__":
    unittest.main()
