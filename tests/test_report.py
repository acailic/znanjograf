import copy
import json
import tempfile
import unittest
from pathlib import Path

from zg import ledger, report
from zg.corpus import Corpus
from tests import helpers

NEVER = {"verified": 0, "stale": [], "never_run": True}


def grade_questions(corpus, grade):
    return [q["id"] for q in corpus.question_list if corpus.topics[q["topic"]]["grade"] == grade]


def grade_edges(corpus, grade):
    return [ledger.edge_id(e) for e in corpus.edge_list if corpus.topics[e["topic"]]["grade"] == grade]


class StatsTest(unittest.TestCase):
    def setUp(self):
        self.corpus = helpers.fixture_corpus()

    def test_fixture_counts(self):
        self.assertEqual(
            report.stats(self.corpus),
            {
                "topics": 8,
                "edges": 8,
                "hard": 6,
                "soft": 2,
                "questions": 32,
                "outcomes": 11,
                "by_grade": {
                    "1": {"topics": 4, "edges": 2, "questions": 16, "outcomes": 5},
                    "2": {"topics": 4, "edges": 6, "questions": 16, "outcomes": 6},
                },
            },
        )

    def test_counts_follow_the_records(self):
        raw = helpers.fixture_raw()
        raw.edges[2].pop(0)  # a hard edge of grade 2
        raw.questions[1].pop(0)
        stats = report.stats(Corpus.from_raw("math", raw))
        self.assertEqual((stats["edges"], stats["hard"], stats["soft"]), (7, 5, 2))
        self.assertEqual(stats["by_grade"]["2"]["edges"], 5)
        self.assertEqual((stats["questions"], stats["by_grade"]["1"]["questions"]), (31, 15))

    def test_outcomes_are_counted_per_grade_of_their_edition(self):
        raw = helpers.fixture_raw()
        raw.editions["g2-2027"] = {
            "edition": "g2-2027", "grade": 2, "applies_from": "2027/28",
            "outcomes": [{"id": "g2-2027-001", "text": "novi ishod", "page": 3}],
        }
        stats = report.stats(Corpus.from_raw("math", raw))
        self.assertEqual(stats["outcomes"], 12)
        self.assertEqual(stats["by_grade"]["2"]["outcomes"], 7)
        self.assertEqual(stats["by_grade"]["1"]["outcomes"], 5)

    def test_stats_change_nothing(self):
        before = copy.deepcopy((self.corpus.topic_list, self.corpus.edge_list, self.corpus.question_list))
        report.stats(self.corpus)
        self.assertEqual((self.corpus.topic_list, self.corpus.edge_list, self.corpus.question_list), before)


class StatusTest(unittest.TestCase):
    def setUp(self):
        self.corpus = helpers.fixture_corpus()
        self.first, self.second = (grade_questions(self.corpus, grade) for grade in (1, 2))
        self.edges = {ledger.edge_id(edge): edge for edge in self.corpus.edge_list}
        self.edges1, self.edges2 = (grade_edges(self.corpus, grade) for grade in (1, 2))

    def test_nothing_was_ever_marked(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.json"
            status = report.status(self.corpus, path)
            self.assertFalse(path.exists())
        self.assertEqual(set(status), {"grades"})
        self.assertEqual(list(status["grades"]), ["1", "2"])
        for grade, counts in (("1", (4, 2, 16)), ("2", (4, 6, 16))):
            row = status["grades"][grade]
            self.assertEqual((row["topics"], row["edges"], row["questions"]), counts)
            self.assertEqual(list(row["gates"]), list(ledger.GATES))
            for gate in ledger.GATES:
                self.assertEqual(row["gates"][gate], NEVER, gate)

    def test_status_counts_what_is_verified_and_what_is_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.json"
            ledger.mark("verify", self.first + self.second[:1], self.corpus.questions, path)
            self.corpus.questions[self.first[0]]["prompt"] += " Odgovori!"
            grades = report.status(self.corpus, path)["grades"]
            self.assertEqual(grades["1"]["gates"]["verify"], {"verified": 15, "stale": [self.first[0]]})
            self.assertEqual(grades["2"]["gates"]["verify"], {"verified": 1, "stale": self.second[1:]})
            self.assertEqual(grades["1"]["gates"]["cueing"], NEVER)  # that gate never ran at all

            ledger.mark("cueing", self.second[:1], self.corpus.questions, path)
            grades = report.status(self.corpus, path)["grades"]
            # the gate ran, but never on this grade: every question here is unverified
            self.assertEqual(grades["1"]["gates"]["cueing"], {"verified": 0, "stale": self.first})
            self.assertEqual(grades["1"]["gates"]["blind-solve"], NEVER)

    def test_status_splits_the_edges_gate_by_grade(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.json"
            ledger.mark("edges", self.edges1, self.edges, path)
            grades = report.status(self.corpus, path)["grades"]
            self.assertEqual(grades["1"]["gates"]["edges"], {"verified": 2, "stale": []})
            self.assertEqual(grades["2"]["gates"]["edges"], {"verified": 0, "stale": self.edges2})
            self.assertEqual(grades["1"]["gates"]["verify"], NEVER)

            ledger.mark("verify", self.first, self.corpus.questions, path)
            self.corpus.edge_list[0]["reason"] = "Izmenjen razlog."
            self.corpus.questions[self.first[3]]["answer"] = "0"
            grades = report.status(self.corpus, path)["grades"]
            self.assertEqual(grades["1"]["gates"]["edges"], {"verified": 1, "stale": [self.edges1[0]]})
            self.assertEqual(grades["1"]["gates"]["verify"], {"verified": 15, "stale": [self.first[3]]})

    def test_status_reads_the_ledger_and_never_writes_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.json"
            ledger.mark("verify", self.first, self.corpus.questions, path)
            before = path.read_bytes()
            report.status(self.corpus, path)
            report.dumps_status(self.corpus, path)
            self.assertEqual(path.read_bytes(), before)

    def test_without_a_path_the_ledger_is_the_one_in_the_corpus_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = helpers.write_corpus(Path(tmp), helpers.fixture_raw())
            loaded = Corpus.load("math", root=root)
            self.assertEqual(report.status(loaded)["grades"]["1"]["gates"]["verify"], NEVER)
            ledger.mark("verify", grade_questions(loaded, 1), loaded.questions, root / "data" / "ledger.json")
            self.assertEqual(report.status(loaded)["grades"]["1"]["gates"]["verify"], {"verified": 16, "stale": []})
            # the gate ran, but nothing of grade 2 was marked
            second = json.loads(report.dumps_status(loaded))["grades"]["2"]["gates"]["verify"]
            self.assertEqual(second, {"verified": 0, "stale": grade_questions(loaded, 2)})


class ReadmeTest(unittest.TestCase):
    def setUp(self):
        self.corpus = helpers.fixture_corpus()
        self.block = report.readme_block(self.corpus)

    def test_block_is_a_table_with_a_row_per_grade_and_a_total_row(self):
        lines = self.block.split("\n")
        self.assertEqual(lines[0], "| Razred | Ishodi programa | Teme | Grane | Zadaci |")
        self.assertEqual(lines[1], "|---|---|---|---|---|")
        self.assertEqual(lines[2:], ["| 1. razred | 5 | 4 | 2 | 16 |", "| 2. razred | 6 | 4 | 6 | 16 |", "| Ukupno | 11 | 8 | 8 | 32 |"])

    def test_block_follows_the_records(self):
        raw = helpers.fixture_raw()
        raw.questions[1].pop(0)
        self.assertIn("| 1. razred | 5 | 4 | 2 | 15 |", report.readme_block(Corpus.from_raw("math", raw)))
        self.assertIn("| Ukupno | 11 | 8 | 8 | 31 |", report.readme_block(Corpus.from_raw("math", raw)))
        del raw.editions["g2-2026"]
        self.assertIn("| 2. razred | 0 | 4 | 6 | 16 |", report.readme_block(Corpus.from_raw("math", raw)))

    def test_block_round_trips_through_check_readme(self):
        start, end = report.START, report.END
        for text in (
            f"# Znanjograf\n\n{start}\n{self.block}\n{end}\n\nOstalo teksta.",
            f"{start}\n{self.block}\n{end}",
            f"{start}\r\n{self.block}\r\n{end}\r\n",
            f"  {start}\n\n{self.block}\n\n  {end}\n",
            f"{start}\n\n{self.block}\n\n{end}",
        ):
            self.assertTrue(report.check_readme(text, self.block), text)
        self.assertTrue(report.check_readme(f"{start}\n{self.block}\n{end}", self.block + "\n"))

    def test_edited_number_fails(self):
        start, end = report.START, report.END
        edited = self.block.replace("| Ukupno | 11 | 8 | 8 | 32 |", "| Ukupno | 11 | 8 | 8 | 33 |")
        self.assertNotEqual(edited, self.block)
        self.assertFalse(report.check_readme(f"{start}\n{edited}\n{end}", self.block))
        self.assertFalse(report.check_readme(f"{start}\n{self.block}\n{end}", edited))
        one_row = self.block.replace("| 2. razred | 6 | 4 | 6 | 16 |", "| 2. razred | 6 | 4 | 5 | 16 |")
        self.assertFalse(report.check_readme(f"{start}\n{one_row}\n{end}", self.block))

    def test_missing_markers_fail(self):
        start, end = report.START, report.END
        for text in (self.block, f"{start}\n{self.block}\n", f"{self.block}\n{end}", f"{end}\n{self.block}\n{start}", ""):
            self.assertFalse(report.check_readme(text, self.block), text)


class DumpsTest(unittest.TestCase):
    def test_dumps_are_the_json_text_of_stats_and_status(self):
        corpus = helpers.fixture_corpus()
        self.assertEqual(report.dumps_stats(corpus), json.dumps(report.stats(corpus), ensure_ascii=False, indent=2))
        self.assertEqual(json.loads(report.dumps_stats(corpus)), report.stats(corpus))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.json"
            ledger.mark("verify", grade_questions(corpus, 1)[:2], corpus.questions, path)
            text = report.dumps_status(corpus, path)
            self.assertEqual(text, json.dumps(report.status(corpus, path), ensure_ascii=False, indent=2))
            self.assertEqual(json.loads(text)["grades"]["1"]["gates"]["verify"], {"verified": 2, "stale": grade_questions(corpus, 1)[2:]})
