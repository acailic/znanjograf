"""V9 on deliberately broken figures: each rule code on one broken example, and the shared fixtures stay valid."""

import copy
import tempfile
import unittest
from pathlib import Path

from zg import jsonio
from zg.checks import figure
from zg.corpus import Corpus
from zg.issues import Issues
from tests import helpers

FIGURES = Path(__file__).parent / "fixtures" / "figures.json"
QUESTION = "mat-brojevi-do-10-q1"  # a grade-1 question
ALT = "Brojevna prava od 0 do 10 sa oznakom na broju 7."
KIND_CODE, ALT_CODE, PARAM, GEOMETRY = "V9-figure-kind", "V9-figure-alt", "V9-figure-param", "V9-figure-geometry"


def fig(kind: str, **params) -> dict:
    """A figure of ``kind`` with a good ``alt`` and ``params`` on top; a value of None drops the parameter."""
    spec = {"kind": kind, "alt": ALT, **params}
    return {name: value for name, value in spec.items() if value is not None}


def numberline(**changes) -> dict:
    return fig(**{"kind": "numberline", "min": 0, "max": 10, "marks": [3, 7], **changes})


def triangle(**changes) -> dict:
    """A 3-4-5 right triangle whose side labels state the true lengths."""
    params = {
        "kind": "polygon",
        "vertices": [[0, 0], [3, 0], [0, 4]],
        "sides": [{"index": 0, "label": "3 cm"}, {"index": 1, "label": "5 cm"}, {"index": 2, "label": "4 cm"}],
        **changes,
    }
    return fig(**params)


# Each breaks exactly one thing; the fragment must appear in the one message it produces.
BROKEN = [
    (numberline(min=None), "„min“"),  # required parameter missing
    (numberline(unit="cm", scale=2), "„scale“"),  # unknown parameter
    (numberline(max="10"), "„max“"),  # wrong type
    (numberline(marks=[3, "7"]), "„marks[1]“"),
    (numberline(step=0), "„step“"),  # out of range
    (numberline(min=10, max=10, marks=[]), "„max“"),
    (numberline(marks=[3, 11]), "„marks“"),  # a mark off the line
    (numberline(min=0, max=100, marks=[]), "„step“"),  # 101 ticks: more than a figure can draw
    (numberline(subticks=1), "„subticks“"),  # a gap cannot be divided into one part
    (numberline(subticks=13), "„subticks“"),
    (numberline(subticks=4.0), "„subticks“"),  # a JSON float is not an integer here
    (numberline(min=0, max=11, marks=[], subticks=11), "„subticks“"),  # 121 parts: one more than a figure can draw
    (numberline(min=0, max=10, step=3, marks=[], subticks=2), "„subticks“"),  # the last tick (9) does not reach max
    (fig("fractionbar", numerator=3, denominator=25), "„denominator“"),
    (fig("fractionbar", numerator=3, denominator=4, shaded=4), "„shaded“"),
    (fig("pie", parts=1, shaded=0), "„parts“"),
    (fig("pie", parts=6, shaded=7), "„shaded“"),
    (fig("dots", rows=0, cols=4), "„rows“"),
    (fig("dots", rows=3, cols=4, count=13), "„count“"),
    (fig("bars", categories=["fudbal"], values=[12]), "„categories“"),
    (fig("bars", categories=["a", "b", "c"], values=[1, 2]), "„values“"),
    (fig("bars", categories=["a", "b"], values=[1, 0]), "„values[1]“"),
    (fig("pictogram", symbol="●", items=[]), "„items“"),
    (fig("pictogram", symbol=" ", items=[{"label": "Mila", "count": 8}]), "„symbol“"),
    (fig("pictogram", symbol="●", items=[{"label": "Mila"}]), "items[0]"),
    (fig("pictogram", symbol="●", items=[{"label": "Mila", "count": 8, "name": "x"}]), "items[0]"),
    (fig("pictogram", symbol="●", items=[{"label": "Mila", "count": -1}]), "items[0].count"),
    (fig("pictogram", symbol="●", items=[{"label": "Mila", "count": 8}], perSymbol=0), "„perSymbol“"),
    (fig("grid", cols=16, rows=3), "„cols“"),
    (fig("grid", cols=4, rows=3, cells=[[0, 4]]), "cells[0]"),
    (fig("polygon", vertices=[[0, 0], [1, 1]]), "„vertices“"),
    (fig("polygon", vertices=[[0, 0], [1, 0], [1, 1]], sides=[{"index": 3, "label": "a"}]), "sides[0]"),
    (fig("polygon", vertices=[[0, 0], [1, 0], [1, 1]], labels=[{"text": "A", "x": 0}]), "labels[0]"),
    (fig("angle", degrees=361), "„degrees“"),
    (fig("angle", degrees=30, vertex=[0]), "„vertex“"),
    (fig("axes", xmin=5, xmax=5, ymin=0, ymax=10), "„xmax“"),
    (fig("axes", xmin=0, xmax=10, ymin=0, ymax=10, points=[{"x": 11, "y": 3, "label": "A"}]), "points[0]"),
    (fig("clock", hour=0, minute=0), "„hour“"),
    (fig("clock", hour=12, minute=60), "„minute“"),
    (fig("clock", hour=True, minute=0), "„hour“"),  # a boolean is not a number
    (fig("table", columns=[], rows=[]), "„columns“"),
    (fig("table", columns=["a", "b"], rows=[["x"]]), "rows[0]"),
    (fig("table", columns=["a", "b"], rows=[["x", 3]]), "rows[0][1]"),
]

# The edges of every range, and every optional parameter left out: all sound.
SOUND = [
    numberline(min=-5, max=5, step=2, marks=[-5, 0, 5], unit="cm"),
    numberline(min=0, max=59, marks=[]),  # exactly as many ticks as a figure can draw
    numberline(subticks=2, marks=[2.5]),
    numberline(min=0, max=10, step=2, subticks=12),
    numberline(min=0, max=60, step=2, marks=[], subticks=4),  # exactly as many parts as a figure can draw (120)
    fig("fractionbar", numerator=1, denominator=24),
    fig("fractionbar", numerator=5, denominator=6, shaded=0),
    fig("fractionbar", numerator=3, denominator=3, shaded=3),
    fig("pie", parts=2, shaded=1),
    fig("pie", parts=12, shaded=12),
    fig("dots", rows=1, cols=1),
    fig("dots", rows=12, cols=12, count=0),
    fig("bars", title="Omiljeni sport", categories=["a", "b"], values=[0.5, 2.5]),
    fig("bars", categories=list("abcdefgh"), values=[1] * 8),
    fig("pictogram", symbol="●", items=[{"label": "Mila", "count": 0}]),
    fig("pictogram", symbol="kg", items=[{"label": "brašno", "count": 5}], perSymbol=2),  # whole numbers: the renderer draws whole symbols
    fig("grid", cols=15, rows=15, cells=[[14, 14], [0, 0]]),
    fig("grid", cols=3, rows=3),
    triangle(),
    fig("polygon", vertices=[[0, 0], [1, 0], [1, 1], [0, 1]], sides=[{"index": 0, "label": "a"}], labels=[{"text": "A", "x": 0, "y": 0}]),
    fig("angle", degrees=0),
    fig("angle", degrees=360, label="α", vertex=[1.5, -2]),
    fig("axes", xmin=-1, xmax=1, ymin=-1, ymax=1, points=[{"x": -1, "y": 1, "label": ""}]),
    fig("clock", hour=1, minute=0),
    fig("clock", hour=12, minute=59),
    fig("table", columns=["a", "b", "c"], rows=[]),  # headers only: a table to fill in
    fig("table", columns=["a"], rows=[["x"], ["y"]]),
]


class FigureCase(unittest.TestCase):
    def check(self, spec: object, question_id: str = QUESTION) -> Issues:
        """V9 on the fixture with ``spec`` as the figure of ``question_id``."""
        raw = helpers.fixture_raw()
        helpers.question(raw, question_id)["figure"] = spec
        issues = Issues()
        figure.run(Corpus.from_raw("math", raw), issues)
        return issues

    def codes(self, spec: object, question_id: str = QUESTION) -> set[str]:
        return self.check(spec, question_id).codes()


class FigureKindAndAltTest(FigureCase):
    def test_kinds_are_the_twelve_of_the_spec(self):
        self.assertEqual(
            figure.KINDS,
            ("numberline", "fractionbar", "pie", "dots", "bars", "pictogram",
             "grid", "polygon", "angle", "axes", "clock", "table"),
        )
        self.assertIsInstance(figure.KINDS, tuple)

    def test_unknown_kind(self):
        self.assertEqual(self.codes(numberline(kind="cube")), {KIND_CODE})

    def test_missing_kind(self):
        spec = numberline()
        del spec["kind"]
        self.assertEqual(self.codes(spec), {KIND_CODE})

    def test_figure_that_is_not_an_object(self):
        for spec in (None, "numberline", ["numberline"]):
            with self.subTest(spec=spec):
                issues = self.check(spec)
                self.assertEqual(issues.codes(), {KIND_CODE})
                self.assertEqual(len(issues), 1)

    def test_alt_of_five_characters(self):
        self.assertEqual(self.codes(numberline(alt="prava")), {ALT_CODE})

    def test_alt_padded_with_spaces_does_not_count(self):
        self.assertEqual(self.codes(numberline(alt=" " + "a" * 19 + " ")), {ALT_CODE})

    def test_alt_of_twenty_characters_passes(self):
        self.assertEqual(self.codes(numberline(alt="a" * 20)), set())

    def test_alt_missing_or_not_text(self):
        self.assertEqual(self.codes(numberline(alt=None)), {ALT_CODE})
        self.assertEqual(self.codes(numberline(alt=42)), {ALT_CODE})

    def test_alt_with_a_formula_is_reported(self):
        # The page shows alt as it stands and reads it whole: a formula would appear with its dollar signs.
        issues = self.check(numberline(alt="Brojevna prava od $0$ do $10$ sa tačkom iznad broja $7$."))
        self.assertEqual(issues.codes(), {ALT_CODE})
        self.assertIn("bez iscrtavanja formula", issues[0].message)
        self.assertEqual(self.codes(numberline(alt="Brojevna prava od 0 do 10 sa tačkom iznad broja 7.")), set())

    def test_a_short_alt_with_a_formula_is_reported_twice(self):
        issues = self.check(numberline(alt="od $0$ do $1$"))
        self.assertEqual(len(issues), 2)
        self.assertEqual(issues.codes(), {ALT_CODE})

    def test_kind_and_alt_are_reported_together(self):
        self.assertEqual(self.codes(numberline(kind="cube", alt="x", foo=1)), {KIND_CODE, ALT_CODE})

    def test_alt_and_parameters_are_reported_together(self):
        self.assertEqual(self.codes(numberline(alt="x", min=None)), {ALT_CODE, PARAM})

    def test_messages(self):
        allowed = "numberline, fractionbar, pie, dots, bars, pictogram, grid, polygon, angle, axes, clock, table"
        self.assertEqual(
            figure.validate(numberline(kind="cube", alt="kratko", min=None)),
            [
                f"nepoznata vrsta slike „cube“; dozvoljene vrste su: {allowed}",
                "„alt“ ima 6 znakova, a treba najmanje 20",
            ],
        )
        self.assertEqual(figure.validate(numberline(min=None)), ["numberline: obavezan parametar „min“ nedostaje"])
        self.assertEqual(
            figure.validate(fig("clock", hour=13, minute=0)),
            ["clock: parametar „hour“ mora biti ceo broj od 1 do 12, a jeste „13“"],
        )
        self.assertEqual(
            figure.validate(fig("polygon", vertices=[[0, 0], [4, 0], [0, 3]], sides=[{"index": 0, "label": "5 cm"}])),
            ["polygon: natpis strane 0 („5 cm“) ne odgovara dužini te strane (4); dozvoljeno je odstupanje do 1 %"],
        )

    def test_the_plural_in_a_message_follows_the_count(self):
        self.assertEqual(figure.validate(numberline(alt="a")), ["„alt“ ima 1 znak, a treba najmanje 20"])
        self.assertEqual(figure.validate(numberline(alt="aa")), ["„alt“ ima 2 znaka, a treba najmanje 20"])
        self.assertEqual(figure.validate(numberline(alt="aaaaa")), ["„alt“ ima 5 znakova, a treba najmanje 20"])
        self.assertEqual(figure.validate(numberline(alt="   ")), ["„alt“ ima 0 znakova, a treba najmanje 20"])


class FigureParamTest(FigureCase):
    def test_one_broken_parameter_gives_one_message_naming_it(self):
        for spec, fragment in BROKEN:
            with self.subTest(spec=spec):
                issues = self.check(spec)
                self.assertEqual([issue.code for issue in issues], [PARAM], [issue.message for issue in issues])
                self.assertEqual(issues[0].path, "data/math/g1/questions.json")
                self.assertEqual(issues[0].where, QUESTION)
                self.assertIn(fragment, issues[0].message)

    def test_sound_figures_are_silent(self):
        for spec in SOUND:
            with self.subTest(spec=spec):
                self.assertEqual(figure.validate(spec), [])
                self.assertEqual(self.check(spec), [])

    def test_every_kind_has_something_that_breaks_it_and_something_that_does_not(self):
        self.assertEqual({spec["kind"] for spec, _ in BROKEN}, set(figure.KINDS))
        self.assertEqual({spec["kind"] for spec in SOUND}, set(figure.KINDS))


class FigureGeometryTest(FigureCase):
    oblique = [[0, 0], [4, 0], [0, 3]]

    def test_side_label_that_contradicts_the_vertices(self):
        spec = fig("polygon", vertices=self.oblique, sides=[{"index": 0, "label": "5 cm"}])
        self.assertEqual(self.codes(spec), {GEOMETRY})

    def test_true_labels_pass(self):
        self.assertEqual(self.check(triangle()), [])

    def test_the_last_side_closes_the_polygon(self):
        self.assertEqual(self.codes(triangle(sides=[{"index": 2, "label": "4 cm"}])), set())
        self.assertEqual(self.codes(triangle(sides=[{"index": 2, "label": "5 cm"}])), {GEOMETRY})

    def test_one_percent_is_the_line(self):
        within = fig("polygon", vertices=self.oblique, sides=[{"index": 0, "label": "4,04 cm"}])
        outside = fig("polygon", vertices=self.oblique, sides=[{"index": 0, "label": "4,05 cm"}])
        self.assertEqual(self.codes(within), set())
        self.assertEqual(self.codes(outside), {GEOMETRY})

    def test_a_side_named_by_a_letter_states_no_length(self):
        sides = [{"index": 0, "label": "a"}, {"index": 1, "label": "b"}, {"index": 2, "label": "c"}]
        self.assertEqual(self.codes(triangle(sides=sides)), set())

    def test_decimal_comma_and_thousands_in_a_label(self):
        small = fig("polygon", vertices=[[0, 0], [1.5, 0], [0, 2]], sides=[{"index": 1, "label": "2,5 cm"}])
        big = fig("polygon", vertices=[[0, 0], [1500, 0], [0, 2000]], sides=[{"index": 1, "label": "2 500 m"}])
        self.assertEqual(self.check(small), [])
        self.assertEqual(self.check(big), [])

    def test_a_false_decimal_comma_is_still_caught(self):
        spec = fig("polygon", vertices=[[0, 0], [1.5, 0], [0, 2]], sides=[{"index": 1, "label": "25 cm"}])
        self.assertEqual(self.codes(spec), {GEOMETRY})

    def test_each_wrong_side_is_its_own_issue(self):
        spec = fig("polygon", vertices=[[0, 0], [1, 0], [1, 1]], sides=[{"index": 0, "label": "5 cm"}, {"index": 1, "label": "5 cm"}])
        self.assertEqual([issue.code for issue in self.check(spec)], [GEOMETRY, GEOMETRY])

    def test_geometry_is_not_judged_on_a_broken_polygon(self):
        spec = fig("polygon", vertices=[[0, 0], [1, 0]], sides=[{"index": 0, "label": "5 cm"}])
        self.assertEqual(self.codes(spec), {PARAM})
        spec = fig("polygon", vertices=self.oblique, sides=[{"index": 0, "label": 5}])
        self.assertEqual(self.codes(spec), {PARAM})


class FigureRunTest(FigureCase):
    def test_issue_points_at_the_question(self):
        issues = self.check(fig("clock", hour=13, minute=0))
        self.assertEqual([(issue.path, issue.where, issue.code) for issue in issues], [("data/math/g1/questions.json", QUESTION, PARAM)])

    def test_a_grade_two_question_points_at_its_own_file(self):
        issues = self.check(fig("clock", hour=13, minute=0), "mat-sabiranje-do-100-q1")
        self.assertEqual((issues[0].path, issues[0].where), ("data/math/g2/questions.json", "mat-sabiranje-do-100-q1"))

    def test_question_without_a_figure_is_not_this_gates_business(self):
        issues = Issues()
        figure.run(Corpus.from_raw("math", helpers.fixture_raw()), issues)
        self.assertEqual(issues, [])

    def test_records_the_other_gates_report_do_not_stop_this_one(self):
        raw = helpers.fixture_raw()
        helpers.question(raw, QUESTION)["figure"] = fig("clock", hour=13, minute=0)
        raw.questions[1].append({"id": ["not", "a", "string"], "figure": fig("cube")})
        raw.questions[1].append(5)  # Corpus.load keeps it; from_raw would not
        with tempfile.TemporaryDirectory() as tmp:
            corpus = Corpus.load("math", root=helpers.write_corpus(Path(tmp), raw))
        issues = Issues()
        figure.run(corpus, issues)
        self.assertEqual(
            [(issue.path, issue.where, issue.code) for issue in issues],
            [("data/math/g1/questions.json", QUESTION, PARAM), ("-", "-", KIND_CODE)],
        )

    def test_run_changes_nothing(self):
        raw = helpers.fixture_raw()
        helpers.question(raw, QUESTION)["figure"] = triangle()
        corpus = Corpus.from_raw("math", raw)
        before = copy.deepcopy(corpus.question_list)
        figure.run(corpus, Issues())
        self.assertEqual(corpus.question_list, before)

    def test_validate_returns_messages_only(self):
        messages = figure.validate(fig("clock", hour=13, minute=0))
        self.assertEqual(messages, ["clock: parametar „hour“ mora biti ceo broj od 1 do 12, a jeste „13“"])
        self.assertEqual(figure.validate(triangle()), [])


class FigureFixtureTest(FigureCase):
    def setUp(self):
        self.specs = jsonio.load(FIGURES)

    def test_one_valid_figure_per_kind(self):
        self.assertEqual(set(self.specs), set(figure.KINDS))
        for kind, spec in self.specs.items():
            with self.subTest(kind):
                self.assertEqual(spec["kind"], kind)
                self.assertEqual(figure.validate(spec), [])
                self.assertEqual(self.check(spec), [])

    def test_every_alt_is_a_real_serbian_description(self):
        for kind, spec in self.specs.items():
            with self.subTest(kind):
                self.assertGreaterEqual(len(spec["alt"].split()), 5)
                self.assertGreaterEqual(len(spec["alt"].strip()), 20)
                self.assertNotRegex(spec["alt"], "[\u0400-\u04ff]")


if __name__ == "__main__":
    unittest.main()


class WholeCountsTest(unittest.TestCase):
    def test_pictogram_counts_must_be_whole(self):
        good = {"kind": "pictogram", "alt": "Slikovni dijagram sa dva reda.", "symbol": "●",
                "items": [{"label": "Mila", "count": 3}], "perSymbol": 1}
        self.assertEqual(figure.validate(good), [])
        for field, value in (("perSymbol", 0.5),):
            self.assertTrue(figure.validate(dict(good, **{field: value})))
        self.assertTrue(figure.validate({**good, "items": [{"label": "Mila", "count": 2.5}]}))
