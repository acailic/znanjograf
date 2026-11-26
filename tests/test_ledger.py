import json
import tempfile
import unittest
from pathlib import Path

from zg import jsonio, ledger
from zg.corpus import Corpus
from tests import helpers

FIRST = "mat-brojevi-do-10-q1"
SECOND = "mat-brojevi-do-10-q2"
THIRD = "mat-brojevi-do-10-q3"
FOURTH = "mat-brojevi-do-10-q4"
FIRST_EDGE = "mat-sabiranje-do-10>mat-brojevi-do-10"


def edge_records(corpus):
    return {ledger.edge_id(edge): edge for edge in corpus.edge_list}


def hashes(corpus, ids):
    return {record_id: ledger.content_hash(corpus.questions[record_id]) for record_id in ids}


class LedgerTest(unittest.TestCase):
    def setUp(self):
        self.corpus = helpers.fixture_corpus()

    def test_hash_is_the_canonical_record_hash_and_ignores_key_order(self):
        self.assertEqual(ledger.content_hash({"b": [2, 3], "a": 1}), jsonio.sha256_obj({"a": 1, "b": [2, 3]}))
        self.assertEqual(ledger.content_hash({"b": [2, 3], "a": 1}), ledger.content_hash({"a": 1, "b": [2, 3]}))
        self.assertNotEqual(ledger.content_hash({"a": 1}), ledger.content_hash({"a": 2}))

    def test_gates_and_file(self):
        self.assertEqual(ledger.GATES, ("verify", "blind-solve", "classify", "cueing", "edges"))
        self.assertEqual(ledger.LEDGER.name, "ledger.json")
        self.assertEqual(ledger.LEDGER.parent.name, "data")

    def test_missing_file_and_missing_directory_load_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(ledger.load_ledger(Path(tmp) / "ledger.json"), {})
            self.assertEqual(ledger.load_ledger(Path(tmp) / "nema" / "data" / "ledger.json"), {})

    def test_broken_ledger_is_an_error_not_an_empty_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.json"
            for text in ("{nije json", "[]", '{"verify": []}'):
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(jsonio.JsonError, msg=text):
                    ledger.load_ledger(path)

    def test_mark_then_load_round_trips_through_a_temp_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "repo" / "data" / "ledger.json"
            ledger.mark("verify", [FIRST, SECOND], self.corpus.questions, path)
            expected = hashes(self.corpus, (FIRST, SECOND))
            self.assertEqual(ledger.load_ledger(path), {"verify": expected})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"verify": expected})

    def test_mark_keeps_the_other_gates_and_the_old_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.json"
            ledger.mark("verify", [FIRST], self.corpus.questions, path)
            ledger.mark("cueing", [SECOND], self.corpus.questions, path)
            ledger.mark("verify", [SECOND], self.corpus.questions, path)
            self.assertEqual(
                ledger.load_ledger(path),
                {"verify": hashes(self.corpus, (FIRST, SECOND)), "cueing": hashes(self.corpus, (SECOND,))},
            )

    def test_file_bytes_do_not_depend_on_the_order_of_marking(self):
        with tempfile.TemporaryDirectory() as tmp:
            one, two = Path(tmp) / "one.json", Path(tmp) / "two.json"
            everything = list(self.corpus.questions)
            ledger.mark("verify", everything, self.corpus.questions, one)
            ledger.mark("cueing", everything, self.corpus.questions, one)
            ledger.mark("cueing", list(reversed(everything)), self.corpus.questions, two)
            ledger.mark("verify", list(reversed(everything)), self.corpus.questions, two)
            self.assertEqual(one.read_bytes(), two.read_bytes())

    def test_nothing_is_stale_while_the_gate_never_ran(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.json"
            self.assertEqual(ledger.stale("verify", self.corpus, path), [])
            ledger.mark("cueing", [FIRST], self.corpus.questions, path)  # another gate ran, not this one
            self.assertEqual(ledger.stale("verify", self.corpus, path), [])

    def test_nothing_is_stale_right_after_marking(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.json"
            ledger.mark("verify", list(self.corpus.questions), self.corpus.questions, path)
            self.assertEqual(ledger.stale("verify", self.corpus, path), [])

    def test_stale_reports_the_changed_record_and_the_unmarked_ones(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.json"
            ledger.mark("verify", [FIRST, SECOND], self.corpus.questions, path)
            unmarked = [qid for qid in self.corpus.questions if qid not in (FIRST, SECOND)]
            self.assertEqual(ledger.stale("verify", self.corpus, path), unmarked)
            self.corpus.questions[FIRST]["answer"] = "10"
            stale = ledger.stale("verify", self.corpus, path)
            self.assertEqual([qid for qid in stale if qid.startswith("mat-brojevi-do-10-")], [FIRST, THIRD, FOURTH])
            self.assertEqual(len(stale), 31)

    def test_stale_is_exactly_the_edited_record_once_everything_is_marked(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.json"
            ledger.mark("verify", list(self.corpus.questions), self.corpus.questions, path)
            prompt = self.corpus.questions[THIRD]["prompt"]
            self.corpus.questions[THIRD]["prompt"] = prompt + " Odgovori!"
            self.assertEqual(ledger.stale("verify", self.corpus, path), [THIRD])
            self.corpus.questions[THIRD]["prompt"] = prompt
            self.assertEqual(ledger.stale("verify", self.corpus, path), [])

    def test_key_order_does_not_make_a_record_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.json"
            ledger.mark("verify", list(self.corpus.questions), self.corpus.questions, path)
            record = self.corpus.questions[FIRST]
            self.corpus.questions[FIRST] = {key: record[key] for key in reversed(list(record))}
            self.assertEqual(ledger.stale("verify", self.corpus, path), [])

    def test_edges_gate_looks_at_edges_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.json"
            records = edge_records(self.corpus)
            ledger.mark("edges", list(records), records, path)
            self.assertEqual(ledger.edge_id(self.corpus.edge_list[0]), FIRST_EDGE)
            self.corpus.questions[FIRST]["answer"] = "10"
            self.assertEqual(ledger.stale("edges", self.corpus, path), [])
            self.corpus.edge_list[0]["reason"] = "Izmenjen razlog."
            self.assertEqual(ledger.stale("edges", self.corpus, path), [FIRST_EDGE])
            self.assertEqual(ledger.stale("verify", self.corpus, path), [])

    def test_unknown_gate_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.json"
            with self.assertRaises(ValueError):
                ledger.mark("Verify", [FIRST], self.corpus.questions, path)
            with self.assertRaises(ValueError):
                ledger.stale("edge", self.corpus, path)
            self.assertFalse(path.exists())

    def test_record_missing_from_records_is_a_plain_key_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(KeyError):
                ledger.mark("verify", [FIRST], {}, Path(tmp) / "ledger.json")

    def test_a_record_deleted_from_the_corpus_is_not_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.json"
            ledger.mark("verify", list(self.corpus.questions), self.corpus.questions, path)
            del self.corpus.questions[THIRD]
            self.assertEqual(ledger.stale("verify", self.corpus, path), [])


class LedgerOnDiskTest(unittest.TestCase):
    """What a real tree loads is what was hashed in memory: the file round trip loses nothing."""

    def test_hashes_survive_a_round_trip_through_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = helpers.write_corpus(Path(tmp), helpers.fixture_raw())
            memory = helpers.fixture_corpus()
            path = root / "data" / "ledger.json"
            ledger.mark("verify", list(memory.questions), memory.questions, path)
            loaded = Corpus.load("math", root=root)
            self.assertEqual(ledger.stale("verify", loaded, path), [])
            loaded.questions[THIRD]["prompt"] += " Odgovori!"
            self.assertEqual(ledger.stale("verify", loaded, path), [THIRD])
