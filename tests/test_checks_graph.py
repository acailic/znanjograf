"""Rules V5 and V6: break the prerequisite graph of the fixture in one way and expect its code."""

import unittest
from unittest import mock

from zg.checks import graph
from zg.corpus import Corpus
from zg.issues import Issues
from tests import helpers

ROOT = "mat-brojevi-do-10"  # grade 1; no edge names it as `topic`, two name it as `requires`
SUM10 = "mat-sabiranje-do-10"
SUM20 = "mat-sabiranje-do-20"
SUM100 = "mat-sabiranje-do-100"
SHAPES = "mat-geometrijski-oblici"  # grade 1; no edge in either direction, carries `root_reason`

TOPICS_ONE = "data/math/g1/topics.json"
TOPICS_TWO = "data/math/g2/topics.json"


def run_graph(raw) -> Issues:
    """The gate over a corpus built from ``raw``."""
    issues = Issues()
    graph.run(Corpus.from_raw("math", raw), issues)
    return issues


class GraphTest(unittest.TestCase):
    def setUp(self):
        self.raw = helpers.fixture_raw()

    def codes(self) -> set[str]:
        return run_graph(self.raw).codes()

    def of(self, code: str) -> list:
        """The issues of one rule on the fixture as it stands."""
        return [issue for issue in run_graph(self.raw) if issue.code == code]

    # ----- the yardstick ------------------------------------------------------------

    def test_fixture_graph_is_clean(self):
        issues = run_graph(self.raw)
        self.assertEqual(issues, [])
        self.assertFalse({code for code in issues.codes() if code.startswith(("V5", "V6"))})

    def test_isolated_topic_that_explains_itself_is_left_alone(self):
        # mat-geometrijski-oblici has no edge at all and says why in `root_reason`.
        self.assertEqual(self.codes(), set())

    def test_gate_never_asks_the_derived_views(self):
        helpers.add_edge(self.raw, ROOT, SUM20, "hard")  # a cycle: the derived views of Corpus would raise
        corpus = Corpus.from_raw("math", self.raw)
        issues = Issues()
        with mock.patch.object(corpus, "_adjacency", side_effect=AssertionError("derived view used")):
            graph.run(corpus, issues)
        self.assertIn("V6-cycle", issues.codes())

    # ----- V5: edges ----------------------------------------------------------------

    def test_edge_to_a_missing_topic(self):
        for topic_id, path in ((SUM10, "data/math/g1/edges.json"), (SUM100, "data/math/g2/edges.json")):
            with self.subTest(topic=topic_id):
                self.raw = helpers.fixture_raw()
                helpers.add_edge(self.raw, topic_id, "mat-nepostojeca", "hard")
                issues = run_graph(self.raw)
                self.assertEqual(issues.codes(), {"V5-edge-endpoint"}, issues)
                self.assertEqual((issues[0].path, issues[0].where), (path, f"{topic_id}>mat-nepostojeca"))

    def test_self_loop(self):
        helpers.add_edge(self.raw, SUM10, SUM10, "hard")
        self.assertEqual(self.codes(), {"V5-self-loop"})

    def test_duplicate_edge(self):
        helpers.add_edge(self.raw, SUM10, ROOT, "soft")  # the same pair already has its hard edge
        self.assertEqual(self.codes(), {"V5-duplicate"})

    def test_reverse_pair(self):
        helpers.add_edge(self.raw, SUM10, SUM20, "hard")  # the reverse of mat-sabiranje-do-20 → mat-sabiranje-do-10
        self.assertEqual(self.codes(), {"V5-reverse-pair", "V6-cycle"})

    def test_grade_order(self):
        del helpers.topic(self.raw, SHAPES)["root_reason"]  # it is about to get an edge of its own
        helpers.add_edge(self.raw, SHAPES, "mat-zadaci-sa-sabiranjem", "hard")  # grade 1 requires grade 2
        self.assertEqual(self.codes(), {"V5-grade-order"})

    def test_soft_edge_redundant_behind_a_mixed_path(self):
        # mat-poredjenje-do-100 → mat-sabiranje-do-10 is soft; the new edge opens a way over
        # mat-brojevi-do-10, and for a soft edge any other way is enough.
        helpers.add_edge(self.raw, ROOT, SUM10, "soft")
        self.assertEqual(
            [(issue.path, issue.where) for issue in self.of("V5-redundant")],
            [("data/math/g2/edges.json", f"mat-poredjenje-do-100>{SUM10}")],
        )

    def test_edge_in_the_file_of_another_grade(self):
        edge = self.raw.edges[1][1]  # mat-sabiranje-do-20 → mat-sabiranje-do-10: two grade 1 topics
        self.raw.edges[1].remove(edge)
        self.raw.edges[2].append(edge)
        issues = run_graph(self.raw)
        self.assertEqual(issues.codes(), {"V5-wrong-file"}, issues)
        self.assertEqual((issues[0].path, issues[0].where), ("data/math/g2/edges.json", f"{SUM20}>{SUM10}"))

    def test_hard_edge_redundant_behind_a_hard_path(self):
        helpers.add_edge(self.raw, SUM100, SUM10, "hard")  # … → mat-sabiranje-do-20 → mat-sabiranje-do-10
        issues = run_graph(self.raw)
        self.assertEqual(issues.codes(), {"V5-redundant"}, issues)
        self.assertEqual((issues[0].path, issues[0].where), ("data/math/g2/edges.json", f"{SUM100}>{SUM10}"))

    def test_soft_edge_redundant_behind_any_path(self):
        helpers.add_edge(self.raw, SUM100, SUM10, "soft")
        self.assertEqual(self.codes(), {"V5-redundant"})

    def test_soft_edge_redundant_behind_a_hard_path(self):
        helpers.add_edge(self.raw, "mat-zadaci-sa-sabiranjem", SUM20, "soft")  # → mat-sabiranje-do-100 → …
        self.assertEqual(self.codes(), {"V5-redundant"})

    def test_hard_edge_stays_when_only_a_soft_path_leads_the_same_way(self):
        # mat-poredjenje-do-100 → mat-brojevi-do-10 is hard; the only other way to the same
        # topic runs over the soft edge mat-poredjenje-do-100 → mat-sabiranje-do-10.
        self.assertEqual(self.of("V5-redundant"), [])

    def test_malformed_edges_do_not_stop_the_gate(self):
        self.raw.edges[1].extend(["nije zapis", {"topic": ROOT}, {"requires": SUM10}, None])
        self.raw.edges[2].append({"topic": "mat-nepostojeca", "requires": ROOT, "strength": "hard", "reason": "x"})
        self.assertEqual(self.codes(), {"V5-edge-endpoint"})

    # ----- V6: the graph ------------------------------------------------------------

    def test_cycle_is_listed_once_per_topic(self):
        helpers.add_edge(self.raw, ROOT, SUM20, "hard")  # mat-brojevi-do-10 → … → mat-sabiranje-do-10 → mat-brojevi-do-10
        issues = self.of("V6-cycle")
        self.assertEqual(sorted(issue.where for issue in issues), sorted([ROOT, SUM20, SUM10]))
        for issue in issues:
            self.assertEqual(issue.path, TOPICS_ONE)
            for topic_id in (ROOT, SUM20, SUM10):
                self.assertIn(topic_id, issue.message)

    def test_topic_of_interlocked_cycles_is_reported_once(self):
        helpers.add_edge(self.raw, ROOT, SUM10, "hard")
        helpers.add_edge(self.raw, ROOT, SUM20, "hard")
        self.assertEqual(sorted(issue.where for issue in self.of("V6-cycle")), sorted([ROOT, SUM20, SUM10]))

    def test_issue_of_a_topic_names_its_file(self):
        helpers.add_edge(self.raw, ROOT, SUM100, "hard")
        self.assertEqual(
            {(issue.path, issue.where) for issue in self.of("V6-cycle")},
            {(TOPICS_ONE, ROOT), (TOPICS_TWO, SUM100), (TOPICS_ONE, SUM20), (TOPICS_ONE, SUM10)},
        )

    def test_root_without_reason(self):
        del helpers.topic(self.raw, ROOT)["root_reason"]
        issues = run_graph(self.raw)
        self.assertEqual(issues.codes(), {"V6-root-reason-missing"})
        self.assertEqual((issues[0].path, issues[0].where), (TOPICS_ONE, ROOT))

    def test_reason_on_a_topic_with_prerequisites(self):
        helpers.topic(self.raw, SUM10)["root_reason"] = "Suvišno objašnjenje."
        self.assertEqual(self.codes(), {"V6-root-reason-unneeded"})

    def test_isolated_topic(self):
        del helpers.topic(self.raw, SHAPES)["root_reason"]
        issues = run_graph(self.raw)
        self.assertEqual(issues.codes(), {"V6-isolated"}, issues)
        self.assertEqual((issues[0].path, issues[0].where), (TOPICS_ONE, SHAPES))


if __name__ == "__main__":
    unittest.main()
