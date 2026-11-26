"""Rules V1–V4, V10 and V11: break the fixture in one way and expect exactly the code of that rule."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from zg.checks import schema
from zg.corpus import Corpus
from zg.issues import Issues
from tests import helpers

ROOT = "mat-brojevi-do-10"  # grade 1; carries `root_reason` and two curriculum references


def run_schema(raw) -> Issues:
    """The gate over a corpus built from ``raw``."""
    issues = Issues()
    schema.run(Corpus.from_raw("math", raw), issues)
    return issues


def examples() -> dict[str, dict]:
    """A valid record of every kind, with every field present, taken from the fixture."""
    raw = helpers.fixture_raw()
    question = helpers.question(raw, "mat-poredjenje-do-100-q3")
    question.update(figure={"kind": "numberline", "alt": "Brojevna prava od 0 do 100."}, round_to=2)
    outcome = dict(raw.editions["g1-2026"]["outcomes"][0], code="M1", level="basic", unit="Brojevi")
    return {
        "topic": helpers.topic(raw, ROOT),
        "edge": raw.edges[1][0],
        "question": question,
        "choice": question["choices"][0],
        "outcome": outcome,
        "theme": raw.editions["g1-2026"]["themes"][0],
        "curriculum_ref": helpers.topic(raw, ROOT)["curriculum"][0],
    }


# Where an issue about a record is reported: (path, where) for one record of every kind.
LOCATIONS = {
    "topic": ("data/math/g1/topics.json", "mat-brojevi-do-10"),
    "edge": ("data/math/g1/edges.json", "mat-sabiranje-do-10>mat-brojevi-do-10"),
    "question": ("data/math/g1/questions.json", "mat-sabiranje-do-10-q1"),
    "choice": ("data/math/g1/questions.json", "mat-geometrijski-oblici-q1.choices[0]"),
    "curriculum_ref": ("data/math/g1/topics.json", "mat-brojevi-do-10.curriculum[0]"),
    "outcome": ("data/curriculum/math/g1-2026.json", "g1-2026-001"),
    "theme": ("data/curriculum/math/g1-2026.json", "themes[0]"),
}


def breakers() -> dict[str, dict]:
    """For every record kind: one call that adds an unknown field, one that removes a required field."""
    def topic(raw):
        return helpers.topic(raw, ROOT)

    def question(raw, question_id):
        return helpers.question(raw, question_id)

    unknown = {
        "topic": lambda raw: topic(raw).update(boja="plava"),
        "edge": lambda raw: raw.edges[1][0].update(dodatno="x"),
        "question": lambda raw: question(raw, "mat-sabiranje-do-10-q1").update(hint="pomoglicu"),
        "choice": lambda raw: question(raw, "mat-geometrijski-oblici-q1")["choices"][0].update(tacno=True),
        "curriculum_ref": lambda raw: topic(raw)["curriculum"][0].update(napomena="x"),
        "outcome": lambda raw: raw.editions["g1-2026"]["outcomes"][0].update(opis="x"),
        "theme": lambda raw: raw.editions["g1-2026"]["themes"][0].update(boja="x"),
    }
    missing = {
        "topic": lambda raw: topic(raw).pop("mastery"),
        "edge": lambda raw: raw.edges[1][0].pop("reason"),
        "question": lambda raw: question(raw, "mat-sabiranje-do-10-q1").pop("prompt"),
        "choice": lambda raw: question(raw, "mat-geometrijski-oblici-q1")["choices"][0].pop("text"),
        "curriculum_ref": lambda raw: topic(raw)["curriculum"][0].pop("match"),
        "outcome": lambda raw: raw.editions["g1-2026"]["outcomes"][0].pop("page"),
        "theme": lambda raw: raw.editions["g1-2026"]["themes"][0].pop("name"),
    }
    return {"unknown": unknown, "missing": missing}


class RecordTest(unittest.TestCase):
    """``check_record`` is the V2 part alone: fields of one record of a known kind."""

    def test_valid_records_raise_nothing(self):
        for kind, record in examples().items():
            with self.subTest(kind=kind):
                issues = Issues()
                schema.check_record(record, kind, "gde", "putanja", issues)
                self.assertEqual(issues, [])

    def test_every_field_rejects_a_value_of_wrong_type(self):
        for kind, valid in examples().items():
            for field in schema.FIELDS[kind]:
                with self.subTest(kind=kind, field=field):
                    record = copy.deepcopy(valid)
                    record[field] = object()
                    issues = Issues()
                    schema.check_record(record, kind, "gde", "putanja", issues)
                    self.assertEqual(issues.codes(), {"V2-type"}, issues)

    def test_unknown_and_missing_field_name_the_field(self):
        issues = Issues()
        schema.check_record({"id": ROOT, "boja": "plava"}, "topic", "gde", "putanja", issues)
        self.assertEqual(issues[0].code, "V2-unknown-field")
        self.assertIn("boja", issues[0].message)
        missing = [issue.message for issue in issues if issue.code == "V2-missing-field"]
        self.assertTrue(any("grade" in message for message in missing), missing)

    def test_record_that_is_not_an_object(self):
        for value in ("tekst", 7, None, ["id"]):
            with self.subTest(value=value):
                issues = Issues()
                schema.check_record(value, "topic", "gde", "putanja", issues)
                self.assertEqual(issues.codes(), {"V2-type"})

    def test_ids_and_enumerations_are_left_to_run(self):
        issues = Issues()
        schema.check_record(dict(examples()["topic"], id="Nevalja", area="algebra", grade=99), "topic", "gde", "putanja", issues)
        self.assertEqual(issues, [])

    def test_nested_records_are_named_by_their_parent(self):
        question = examples()["question"]
        question["choices"][1]["tacno"] = True
        issues = Issues()
        schema.check_record(question, "question", "pitanje", "putanja", issues)
        self.assertEqual([issue.where for issue in issues], ["pitanje.choices[1]"])

    def test_iter_strings_walks_values_not_keys(self):
        record = {"a": "prvi", "b": ["drugi", {"c": "treći"}], "d": 5, "kljuc": None}
        self.assertEqual(list(schema.iter_strings(record)), ["prvi", "drugi", "treći"])
        self.assertEqual(list(schema.iter_strings("samo")), ["samo"])
        self.assertEqual(list(schema.iter_strings(5)), [])


class SchemaTest(unittest.TestCase):
    def setUp(self):
        self.raw = helpers.fixture_raw()

    def codes(self) -> set[str]:
        return run_schema(self.raw).codes()

    def parts(self) -> dict:
        """The records the type tests break."""
        raw = self.raw
        return {
            "topic": helpers.topic(raw, ROOT),
            "edge": raw.edges[1][0],
            "question": helpers.question(raw, "mat-poredjenje-do-100-q3"),
            "outcome": raw.editions["g1-2026"]["outcomes"][0],
            "theme": raw.editions["g1-2026"]["themes"][0],
        }

    # ----- the yardstick ------------------------------------------------------------

    def test_fixture_has_no_structural_issue(self):
        issues = run_schema(self.raw)
        self.assertEqual(issues, [])
        self.assertFalse({code for code in issues.codes() if code.startswith(("V2", "V3", "V4", "V10", "V11"))})

    def test_optional_fields_may_be_present(self):
        helpers.question(self.raw, "mat-sabiranje-do-100-q1").update(figure={"kind": "numberline"}, round_to=2)
        self.raw.editions["g2-2026"]["outcomes"][0].update(code="M2", level="medium", area="numbers", unit="Brojevi")
        self.assertEqual(self.codes(), set())

    # ----- V2: fields ---------------------------------------------------------------

    def test_unknown_field_on_every_kind(self):
        for kind, break_fixture in breakers()["unknown"].items():
            with self.subTest(kind=kind):
                self.raw = helpers.fixture_raw()
                break_fixture(self.raw)
                issues = run_schema(self.raw)
                self.assertEqual(issues.codes(), {"V2-unknown-field"}, issues)
                self.assertEqual([(issue.path, issue.where) for issue in issues], [LOCATIONS[kind]])

    def test_missing_field_on_every_kind(self):
        for kind, break_fixture in breakers()["missing"].items():
            with self.subTest(kind=kind):
                self.raw = helpers.fixture_raw()
                break_fixture(self.raw)
                issues = run_schema(self.raw)
                self.assertEqual(issues.codes(), {"V2-missing-field"}, issues)
                self.assertEqual({(issue.path, issue.where) for issue in issues}, {LOCATIONS[kind]})

    def test_wrong_type(self):
        cases = {
            "mastery is not a list": lambda p: p["topic"].update(mastery="sve nabroji"),
            "one criterion only": lambda p: p["topic"].update(mastery=["samo jedan"]),
            "four criteria": lambda p: p["topic"].update(mastery=["a", "b", "c", "d"]),
            "blank criterion": lambda p: p["topic"].update(mastery=["dobar", " "]),
            "criterion that is not text": lambda p: p["topic"].update(mastery=["dobar", 5]),
            "grade as text": lambda p: p["topic"].update(grade="1"),
            "grade as decimal": lambda p: p["topic"].update(grade=1.0),
            "grade as truth value": lambda p: p["topic"].update(grade=True),
            "root_reason as number": lambda p: p["topic"].update(root_reason=5),
            "blank name": lambda p: p["topic"].update(name="  "),
            "curriculum as text": lambda p: p["topic"].update(curriculum="g1-2026-001"),
            "curriculum of strings": lambda p: p["topic"].update(curriculum=["g1-2026-001"]),
            "choices as text": lambda p: p["question"].update(choices="a, b, c"),
            "choices of strings": lambda p: p["question"].update(choices=["a", "b"]),
            "points_to as list": lambda p: p["question"].update(points_to=["mat-brojevi-do-10"]),
            "points_to with an empty target": lambda p: p["question"].update(points_to={"a": ""}),
            "figure as text": lambda p: p["question"].update(figure="slika.png"),
            "round_to as text": lambda p: p["question"].update(round_to="2"),
            "edge reason as number": lambda p: p["edge"].update(reason=7),
            "edge strength as number": lambda p: p["edge"].update(strength=1),
            "outcome page as text": lambda p: p["outcome"].update(page="12"),
            "theme hours as text": lambda p: p["theme"].update(hours="27"),
            "theme content as text": lambda p: p["theme"].update(content="Brojevi do 10"),
        }
        for label, break_fixture in cases.items():
            with self.subTest(label=label):
                self.raw = helpers.fixture_raw()
                break_fixture(self.parts())
                self.assertEqual(self.codes(), {"V2-type"})

    def test_record_that_is_not_an_object(self):
        # Read from disk: Corpus.load keeps such a record for the gates to see.
        self.raw.edges[1].append(None)
        with tempfile.TemporaryDirectory() as tmp:
            base = helpers.write_corpus(Path(tmp), self.raw) / "data" / "math"
            (base / "g1" / "topics.json").write_text(json.dumps(self.raw.topics[1] + ["nije zapis"], ensure_ascii=False), encoding="utf-8")
            (base / "g2" / "questions.json").write_text(json.dumps(self.raw.questions[2] + [7]), encoding="utf-8")
            issues = Issues()
            schema.run(Corpus.load("math", root=tmp), issues)
        self.assertEqual(issues.codes(), {"V2-type"})
        self.assertEqual(
            {(issue.path, issue.where) for issue in issues},
            {("data/math/g1/topics.json", "topics[4]"), ("data/math/g2/questions.json", "questions[16]"),
             ("data/math/g1/edges.json", "edges[2]")},
        )

    def test_record_without_id_is_named_by_its_position(self):
        self.raw.topics[2].append({"grade": 2})
        self.raw.questions[1].append({"topic": ROOT, "nepoznato": 1})
        issues = run_schema(self.raw)
        self.assertEqual(issues.codes(), {"V2-missing-field", "V2-unknown-field"})
        self.assertEqual(
            {(issue.path, issue.where) for issue in issues},
            {("data/math/g2/topics.json", "topics[4]"), ("data/math/g1/questions.json", "questions[16]")},
        )

    # ----- V3: ids ------------------------------------------------------------------

    def test_topic_id_with_uppercase_letter(self):
        helpers.topic(self.raw, ROOT)["id"] = "Mat-Brojevi"
        issues = run_schema(self.raw)
        self.assertIn("V3-id-format", issues.codes())
        issue = next(i for i in issues if i.code == "V3-id-format")
        self.assertEqual((issue.path, issue.where), ("data/math/g1/topics.json", "Mat-Brojevi"))

    def test_malformed_topic_ids(self):
        too_long = "mat-" + "a" * 45
        self.assertEqual(len(too_long), 49)
        for bad in ("mat_brojevi", "mat-", "brojevi", "mat-brojevi ", "mat-бројеви", too_long):
            with self.subTest(bad=bad):
                self.raw = helpers.fixture_raw()
                helpers.topic(self.raw, ROOT)["id"] = bad
                self.assertIn("V3-id-format", self.codes())

    def test_longest_topic_id_is_accepted(self):
        longest = "mat-" + "a" * 44
        self.assertEqual(len(longest), 48)
        helpers.topic(self.raw, ROOT)["id"] = longest
        self.assertNotIn("V3-id-format", self.codes())

    def test_registry_id_must_be_a_topic_id(self):
        self.raw.registry.append("mat_loš id")
        issues = run_schema(self.raw)
        self.assertEqual(issues.codes(), {"V3-id-format"})
        self.assertEqual((issues[0].path, issues[0].where), ("data/registry.json", "mat_loš id"))

    def test_outcome_id_and_edition_id_formats(self):
        self.raw.editions["g1-2026"]["outcomes"][0]["id"] = "g1-26-001"
        self.raw.editions["g2-26"] = self.raw.editions.pop("g2-2026")
        issues = run_schema(self.raw)
        self.assertEqual(issues.codes(), {"V3-id-format"})
        self.assertEqual(
            {(issue.path, issue.where) for issue in issues},
            {("data/curriculum/math/g1-2026.json", "g1-26-001"), ("data/curriculum/math/g2-26.json", "g2-26")},
        )

    def test_curriculum_reference_ids(self):
        for field, bad in (("edition", "g1-26"), ("outcome", "ishod-1"), ("outcome", "g1-2026-1")):
            with self.subTest(field=field, bad=bad):
                self.raw = helpers.fixture_raw()
                helpers.topic(self.raw, ROOT)["curriculum"][0][field] = bad
                issues = run_schema(self.raw)
                self.assertEqual(issues.codes(), {"V3-id-format"}, issues)
                self.assertEqual((issues[0].path, issues[0].where), LOCATIONS["curriculum_ref"])

    def test_duplicate_topic_id(self):
        self.raw.topics[2].append(dict(helpers.topic(self.raw, ROOT)))
        self.assertEqual(self.codes(), {"V3-id-duplicate"})

    def test_duplicate_question_id(self):
        self.raw.questions[2].append(dict(helpers.question(self.raw, "mat-sabiranje-do-100-q1")))
        self.assertEqual(self.codes(), {"V3-id-duplicate"})

    def test_outcome_id_twice_in_one_edition(self):
        self.raw.editions["g2-2026"]["outcomes"].append(dict(self.raw.editions["g2-2026"]["outcomes"][0]))
        self.assertEqual(self.codes(), {"V3-id-duplicate"})

    def test_topic_absent_from_registry(self):
        self.raw.registry.remove(ROOT)
        issues = run_schema(self.raw)
        self.assertEqual(issues.codes(), {"V3-id-unregistered"})
        self.assertEqual((issues[0].path, issues[0].where), LOCATIONS["topic"])

    def test_question_id_must_follow_its_topic(self):
        for bad in ("mat-sabiranje-do-10-p1", "mat-sabiranje-do-10-q", "mat-sabiranje-do-10-Q1", "pitanje-1",
                    "mat-sabiranje-do-20-q9"):
            with self.subTest(bad=bad):
                self.raw = helpers.fixture_raw()
                helpers.question(self.raw, "mat-sabiranje-do-10-q1")["id"] = bad
                self.assertEqual(self.codes(), {"V3-qid-format"})

    def test_question_id_may_have_several_digits(self):
        helpers.question(self.raw, "mat-sabiranje-do-10-q1")["id"] = "mat-sabiranje-do-10-q12"
        self.assertEqual(self.codes(), set())

    def test_question_on_unknown_topic(self):
        question = helpers.question(self.raw, "mat-sabiranje-do-10-q1")
        question["id"] = "mat-nepostojeca-q1"
        question["topic"] = "mat-nepostojeca"
        issues = run_schema(self.raw)
        self.assertEqual(issues.codes(), {"V3-id-unknown"})

    def test_points_to_unknown_topic(self):
        helpers.question(self.raw, "mat-poredjenje-do-100-q3")["points_to"] = {"a": "mat-nepostojeca"}
        issues = run_schema(self.raw)
        self.assertEqual(issues.codes(), {"V3-id-unknown"})
        self.assertEqual(issues[0].where, "mat-poredjenje-do-100-q3")

    # ----- V4: enumerations and grades ----------------------------------------------

    def test_value_outside_enumeration(self):
        cases = {
            "topic area": lambda p: p["topic"].update(area="algebra"),
            "topic kind": lambda p: p["topic"].update(kind="veština"),
            "edge strength": lambda p: p["edge"].update(strength="medium"),
            "question level": lambda p: p["question"].update(level="napredni"),
            "question type": lambda p: p["question"].update(type="tekst"),
            "curriculum match": lambda p: p["topic"]["curriculum"][0].update(match="lose"),
            "outcome level": lambda p: p["outcome"].update(level="težak"),
            "outcome area": lambda p: p["outcome"].update(area="logika"),
            "theme area": lambda p: p["theme"].update(area="logika"),
        }
        for label, break_fixture in cases.items():
            with self.subTest(label=label):
                self.raw = helpers.fixture_raw()
                break_fixture(self.parts())
                self.assertEqual(self.codes(), {"V4-enum"})

    def test_grade_outside_primary_school(self):
        for grade in (0, 9, -1):
            with self.subTest(grade=grade):
                self.raw = helpers.fixture_raw()
                helpers.topic(self.raw, ROOT)["grade"] = grade
                self.assertEqual(self.codes(), {"V4-grade"})

    def test_every_grade_of_primary_school_is_accepted(self):
        for grade in range(1, 9):
            with self.subTest(grade=grade):
                self.raw = helpers.fixture_raw()
                helpers.topic(self.raw, ROOT)["grade"] = grade
                self.assertNotIn("V4-grade", self.codes())

    # ----- V10: formulas ------------------------------------------------------------

    def test_unbalanced_dollar_sign(self):
        helpers.topic(self.raw, ROOT)["summary"] += " Košta $5."
        issues = run_schema(self.raw)
        self.assertEqual(issues.codes(), {"V10-dollar"})
        self.assertEqual((issues[0].path, issues[0].where), LOCATIONS["topic"])

    def test_empty_formula(self):
        for text in ("Ima $$ ovde.", "Prazno $ $ ovde.", "$$$$"):
            with self.subTest(text=text):
                self.raw = helpers.fixture_raw()
                helpers.topic(self.raw, ROOT)["summary"] = text
                self.assertEqual(self.codes(), {"V10-dollar"})

    def test_dollar_sign_in_a_nested_string(self):
        def mastery_item(raw):
            helpers.topic(raw, ROOT)["mastery"][1] = "broji do $10"

        cases = {
            "choice text": lambda raw: helpers.question(raw, "mat-geometrijski-oblici-q1")["choices"][0].update(text="$$"),
            "mastery item": mastery_item,
            "edge reason": lambda raw: raw.edges[1][0].update(reason="Zbog $"),
            "outcome text": lambda raw: raw.editions["g2-2026"]["outcomes"][4].update(text="koristi znak $"),
            "theme content": lambda raw: raw.editions["g1-2026"]["themes"][0].update(content=["Brojevi do $10"]),
        }
        for label, break_fixture in cases.items():
            with self.subTest(label=label):
                self.raw = helpers.fixture_raw()
                break_fixture(self.raw)
                self.assertEqual(self.codes(), {"V10-dollar"})

    def test_balanced_formulas_pass(self):
        topic = helpers.topic(self.raw, ROOT)
        topic["summary"] = "Za $3{,}5$ cm i $15\\,\\%$ važi $a < b$."
        helpers.question(self.raw, "mat-geometrijski-oblici-q3")["choices"][0]["text"] = "Neki $x$ i $y$"
        self.assertEqual(self.codes(), set())

    # ----- V11: aliases -------------------------------------------------------------

    def test_alias_target_must_be_existing_topics(self):
        for value in (["mat-nepostojeci"], [], "mat-brojevi-do-10", ["mat-brojevi-do-10", 7], None):
            with self.subTest(value=value):
                self.raw = helpers.fixture_raw()
                self.raw.aliases["mat-stari"] = value
                issues = run_schema(self.raw)
                self.assertEqual(issues.codes(), {"V11-alias-target"}, issues)
                self.assertEqual((issues[0].path, issues[0].where), ("data/aliases.json", "mat-stari"))

    def test_alias_chain(self):
        self.raw.aliases["mat-brojevi-do-10"] = ["mat-sabiranje-do-10"]  # target of „mat-brojevi“, itself an alias
        issues = run_schema(self.raw)
        self.assertEqual(issues.codes(), {"V11-alias-chain"})
        self.assertEqual((issues[0].path, issues[0].where), ("data/aliases.json", "mat-brojevi-do-10"))

    def test_alias_key_must_be_a_topic_id(self):
        self.raw.aliases["Stari_ID"] = ["mat-brojevi-do-10"]
        issues = run_schema(self.raw)
        self.assertEqual(issues.codes(), {"V3-id-format"})
        self.assertEqual((issues[0].path, issues[0].where), ("data/aliases.json", "Stari_ID"))

    def test_alias_table_that_is_not_an_object(self):
        self.raw.aliases = ["mat-brojevi"]
        issues = run_schema(self.raw)
        self.assertEqual([(issue.code, issue.path, issue.where) for issue in issues], [("V2-type", "data/aliases.json", "-")])

    # ----- V1: files that failed to load --------------------------------------------

    def test_load_errors_are_reported_first(self):
        helpers.topic(self.raw, ROOT)["boja"] = "plava"
        corpus = Corpus.from_raw("math", self.raw)
        corpus.load_errors.append(("data/math/g1/topics.json", "nevaljan JSON"))
        issues = Issues()
        schema.run(corpus, issues)
        self.assertEqual([issue.code for issue in issues], ["V1-json", "V2-unknown-field"])
        self.assertEqual((issues[0].path, issues[0].where, issues[0].message), ("data/math/g1/topics.json", "-", "nevaljan JSON"))

    def test_broken_file_on_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = helpers.write_corpus(Path(tmp), helpers.fixture_raw())
            (root / "data" / "math" / "g1" / "topics.json").write_text("[{", encoding="utf-8")
            corpus = Corpus.load("math", root=root)
        issues = Issues()
        schema.run(corpus, issues)
        self.assertEqual([issue.code for issue in issues][:1], ["V1-json"])
        self.assertEqual([issue.path for issue in issues if issue.code == "V1-json"], ["data/math/g1/topics.json"])


class SchemaContractTest(unittest.TestCase):
    """Names and shapes the other gates import."""

    def test_record_kinds_and_required_fields(self):
        self.assertEqual(set(schema.FIELDS), {"topic", "edge", "question", "choice", "outcome", "theme", "curriculum_ref"})
        self.assertEqual({kind: fields - schema.REQUIRED[kind] for kind, fields in schema.FIELDS.items()}, {
            "topic": {"root_reason"},
            "edge": set(),
            "question": {"figure", "choices", "points_to", "round_to"},
            "choice": set(),
            "outcome": {"code", "level", "area", "unit"},
            "theme": {"area", "hours", "content", "page"},
            "curriculum_ref": set(),
        })
        for kind in schema.FIELDS:
            self.assertLessEqual(schema.REQUIRED[kind], schema.FIELDS[kind])

    def test_enums(self):
        self.assertEqual(set(schema.ENUMS), {"area", "kind", "level", "type", "strength", "match", "outcome_level"})
        self.assertEqual(schema.ENUMS["area"], {"numbers", "geometry", "data"})
        self.assertEqual(schema.ENUMS["kind"], {"concept", "procedure", "problem", "reasoning"})
        self.assertEqual(schema.ENUMS["level"], {"basic", "standard"})
        self.assertEqual(schema.ENUMS["type"], {"numeric", "choice"})
        self.assertEqual(schema.ENUMS["strength"], {"hard", "soft"})
        self.assertEqual(schema.ENUMS["match"], {"exact", "partial"})
        self.assertEqual(schema.ENUMS["outcome_level"], {"basic", "medium", "advanced"})

    def test_id_patterns(self):
        self.assertRegex("mat-sabiranje-do-20", schema.TOPIC_ID)
        self.assertNotRegex("Mat-sabiranje-do-20", schema.TOPIC_ID)
        self.assertRegex("g1-2026-012", schema.OUTCOME_ID)
        self.assertNotRegex("g1-26-012", schema.OUTCOME_ID)
        self.assertNotRegex("g9-2026-012", schema.OUTCOME_ID)
        self.assertRegex("g1-2026", schema.EDITION_ID)
        self.assertNotRegex("g1-2026-012", schema.EDITION_ID)
        match = schema.QUESTION_ID.match("mat-foo-q5-q12")
        self.assertEqual((match["topic"], match["number"]), ("mat-foo-q5", "12"))
        self.assertIsNone(schema.QUESTION_ID.match("mat-foo-bar"))

    def test_id_patterns_take_the_whole_id(self):
        for pattern, text in ((schema.TOPIC_ID, "mat-brojevi\n"), (schema.OUTCOME_ID, "g1-2026-00１")):
            with self.subTest(pattern=pattern.pattern):
                self.assertIsNone(pattern.match(text))


if __name__ == "__main__":
    unittest.main()


class EditionHeaderTest(unittest.TestCase):
    def codes_after(self, mutate):
        raw = helpers.fixture_raw()
        mutate(raw)
        issues = Issues()
        schema.run(Corpus.from_raw("math", raw), issues)
        return issues

    def test_an_unknown_top_level_field_is_reported(self):
        issues = self.codes_after(lambda raw: raw.editions["g1-2026"].update({"nesto": 1}))
        self.assertIn("V2-unknown-field", issues.codes())
        self.assertTrue(any(i.where == "nesto" for i in issues))

    def test_applies_from_must_be_text(self):
        issues = self.codes_after(lambda raw: raw.editions["g1-2026"].update({"applies_from": 2026}))
        self.assertIn("V2-type", issues.codes())

    def test_the_fixture_header_is_clean(self):
        self.assertEqual(self.codes_after(lambda raw: None).codes(), set())
