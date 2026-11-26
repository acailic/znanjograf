import copy
import importlib.util
import sys
import types
import unittest
import unicodedata
from unittest import mock

from zg import blind
from tests import helpers

TRANSLIT = "zg.translit.rules"
FORBIDDEN = {"answer", "check", "explanation", "level", "topic", "points_to", "round_to"}
NUMERIC = "mat-sabiranje-do-20-q3"
CHOICE = "mat-geometrijski-oblici-q1"  # four options, the correct one is "b"


def grade_questions(corpus, grade):
    return [q for q in corpus.question_list if corpus.topics[q["topic"]]["grade"] == grade]


def clean_answers(corpus, grade):
    """What a perfect blind solver returns: the bank's own answer and check, nothing assumed, no cue."""
    answers = {}
    for question in grade_questions(corpus, grade):
        answers[question["id"]] = {
            "answer": question["answer"],
            "check": question["check"],
            "unique": True,
            "assumptions": [],
            "distractors": {c["id"]: 0 for c in question.get("choices", []) if c["id"] != question["answer"]},
        }
    return answers


def all_keys(node):
    if isinstance(node, dict):
        return set(node).union(*(all_keys(value) for value in node.values()))
    if isinstance(node, list):
        return set().union(*(all_keys(value) for value in node))
    return set()


def letters(text, script):
    return {char for char in text if char.isalpha() and unicodedata.name(char).startswith(script)}


def translit_available():
    try:
        return importlib.util.find_spec(TRANSLIT) is not None
    except (ImportError, ValueError):
        return False


class SheetTest(unittest.TestCase):
    def setUp(self):
        self.corpus = helpers.fixture_corpus()
        self.bank = self.corpus.questions

    def test_latin_sheet_shows_only_what_a_pupil_sees(self):
        sheet = blind.make_sheet(self.corpus, 1, script="lat", seed=7)
        self.assertEqual(set(sheet), {"grade", "script", "items"})
        self.assertEqual((sheet["grade"], sheet["script"]), (1, "lat"))
        self.assertEqual({item["id"] for item in sheet["items"]}, {q["id"] for q in grade_questions(self.corpus, 1)})
        for item in sheet["items"]:
            self.assertEqual(set(item), {"id", "prompt", "figure", "choices"})
            self.assertIsNone(item["figure"])
            self.assertEqual(item["prompt"], self.bank[item["id"]]["prompt"])
            self.assertEqual(item["choices"], [{"id": c["id"], "text": c["text"]} for c in self.bank[item["id"]].get("choices", [])])
            for choice in item["choices"]:
                self.assertEqual(set(choice), {"id", "text"})
        self.assertEqual(all_keys(sheet) & FORBIDDEN, set())

    def test_order_is_random_and_reproducible_from_the_seed(self):
        file_order = [q["id"] for q in grade_questions(self.corpus, 1)]
        seeded = blind.make_sheet(self.corpus, 1, script="lat", seed=3)
        again = blind.make_sheet(self.corpus, 1, script="lat", seed=3)
        other = blind.make_sheet(self.corpus, 1, script="lat", seed=4)
        self.assertEqual(seeded, again)
        self.assertNotEqual([item["id"] for item in seeded["items"]], file_order)
        self.assertNotEqual([item["id"] for item in seeded["items"]], [item["id"] for item in other["items"]])
        self.assertEqual(sorted(item["id"] for item in seeded["items"]), sorted(file_order))

    def test_each_grade_gets_only_its_own_questions(self):
        sheet = blind.make_sheet(self.corpus, 2, script="lat", seed=1)
        self.assertEqual(len(sheet["items"]), 16)
        for item in sheet["items"]:
            self.assertEqual(self.corpus.topics[self.bank[item["id"]]["topic"]]["grade"], 2)
        self.assertEqual(blind.make_sheet(self.corpus, 3, script="lat")["items"], [])

    def test_figure_is_a_copy_of_the_declaration(self):
        figure = {"kind": "numberline", "alt": "Brojevna prava od 0 do 10", "min": 0, "max": 10, "ticks": [6]}
        self.bank["mat-brojevi-do-10-q1"]["figure"] = figure
        sheet = blind.make_sheet(self.corpus, 1, script="lat", seed=0)
        item = next(item for item in sheet["items"] if item["id"] == "mat-brojevi-do-10-q1")
        self.assertEqual(item["figure"], figure)
        self.assertIsNot(item["figure"], figure)
        item["figure"]["ticks"].append(7)
        self.assertEqual(figure["ticks"], [6])

    def test_unknown_script_is_refused(self):
        with self.assertRaises(ValueError):
            blind.make_sheet(self.corpus, 1, script="cir")

    def test_cyrillic_sheet_needs_the_translit_module(self):
        with mock.patch.dict(sys.modules, {TRANSLIT: None}):
            with self.assertRaisesRegex(RuntimeError, "translit nije dostupan"):
                blind.make_sheet(self.corpus, 1)

    def test_cyrillic_sheet_transliterates_text_and_leaves_ids(self):
        fake = types.ModuleType(TRANSLIT)
        lexicons = []

        def shout(text, lexicon=None):  # any text transform will do: we only check where it is applied
            lexicons.append(lexicon)
            return text.upper()

        fake.to_cyrillic = shout
        figure = {"kind": "pictogram", "alt": "Prava od 0 do 10", "symbol": "ab", "items": [{"label": "polovina", "count": 1}]}
        self.bank["mat-brojevi-do-10-q1"]["figure"] = figure
        before = copy.deepcopy(self.corpus.question_list)
        with mock.patch.dict(sys.modules, {TRANSLIT: fake}):
            sheet = blind.make_sheet(self.corpus, 1, seed=5)
        items = {item["id"]: item for item in sheet["items"]}
        self.assertEqual(sheet["script"], "cyr")
        self.assertEqual(items["mat-brojevi-do-10-q1"]["prompt"], self.bank["mat-brojevi-do-10-q1"]["prompt"].upper())
        # what the site keeps in Latin because code reads it: kind, the pictogram symbol
        self.assertEqual(
            items["mat-brojevi-do-10-q1"]["figure"],
            {"kind": "pictogram", "alt": "PRAVA OD 0 DO 10", "symbol": "ab", "items": [{"label": "POLOVINA", "count": 1}]},
        )
        # the corpus digraph lexicon travels with every text, exactly as it does in the built site
        self.assertTrue(lexicons)
        self.assertTrue(all(handed is self.corpus.lexicon for handed in lexicons))
        self.assertEqual(
            items[CHOICE]["choices"],
            [{"id": "a", "text": "KVADRAT"}, {"id": "b", "text": "TROUGAO"}, {"id": "c", "text": "KRUG"}, {"id": "d", "text": "PRAVOUGAONIK"}],
        )
        self.assertEqual(all_keys(sheet) & FORBIDDEN, set())
        self.assertEqual(self.corpus.question_list, before)

    @unittest.skipUnless(translit_available(), "translit nije dostupan")
    def test_cyrillic_sheet_is_in_cyrillic(self):
        sheet = blind.make_sheet(self.corpus, 1, script="cyr", seed=0)
        items = {item["id"]: item for item in sheet["items"]}
        # A prompt whose only `$…$` spans hold digits: nothing Latin is left to protect.
        prompt = items["mat-sabiranje-do-10-q3"]["prompt"]
        self.assertEqual(letters(prompt, "LATIN"), set())
        self.assertTrue(letters(prompt, "CYRILLIC"))
        option = items[CHOICE]["choices"][1]["text"]
        self.assertEqual(letters(option, "LATIN"), set())
        self.assertEqual(len(letters(option, "CYRILLIC")), len(letters("trougao", "LATIN")))

    @unittest.skipUnless(translit_available(), "translit nije dostupan")
    def test_cyrillic_sheet_spells_digraph_words_as_the_site_does(self):
        from zg.translit import rules

        prompt = "Šta je injekcija?"  # the fixture lexicon splits this n|j
        self.assertEqual(self.corpus.lexicon.get("injekcija"), "split:n|j")
        self.bank["mat-brojevi-do-10-q1"]["prompt"] = prompt
        sheet = blind.make_sheet(self.corpus, 1, seed=0)
        shown = next(item["prompt"] for item in sheet["items"] if item["id"] == "mat-brojevi-do-10-q1")
        self.assertEqual(shown, rules.to_cyrillic(prompt, self.corpus.lexicon))
        self.assertNotEqual(shown, rules.to_cyrillic(prompt))  # without the lexicon the word is spelled another way


class DiffTest(unittest.TestCase):
    def setUp(self):
        self.corpus = helpers.fixture_corpus()
        self.answers = clean_answers(self.corpus, 1)

    def diff(self):
        return blind.diff(self.corpus, 1, self.answers)

    def test_clean_answer_set_passes(self):
        for grade in (1, 2):
            self.assertEqual(blind.diff(self.corpus, grade, clean_answers(self.corpus, grade)), [])

    def test_wrong_answer_fails(self):
        self.answers[NUMERIC]["answer"] = "16"
        self.assertEqual(self.diff(), [{"id": NUMERIC, "reasons": ["answer"]}])

    def test_answers_are_compared_as_stripped_text(self):
        self.answers[NUMERIC]["answer"] = " 15 "
        self.assertEqual(self.diff(), [])
        self.answers[NUMERIC]["answer"] = 15
        self.assertEqual(self.diff(), [])

    def test_own_check_must_match(self):
        self.answers[NUMERIC]["check"] = "(+ 8 6)"
        self.assertEqual(self.diff(), [{"id": NUMERIC, "reasons": ["check"]}])

    def test_check_ignores_whitespace(self):
        self.answers[NUMERIC]["check"] = "\t(+   8\n7) "
        self.assertEqual(self.diff(), [])

    def test_unique_must_be_exactly_true(self):
        for value in (False, 1, "true", None):
            self.answers[NUMERIC]["unique"] = value
            self.assertEqual(self.diff(), [{"id": NUMERIC, "reasons": ["unique"]}], value)

    def test_assumptions_must_be_empty(self):
        self.answers[NUMERIC]["assumptions"] = ["Pretpostavljam da su kuvanice cele."]
        self.assertEqual(self.diff(), [{"id": NUMERIC, "reasons": ["assumptions"]}])

    def test_defensible_distractor_fails(self):
        self.answers[CHOICE]["distractors"]["a"] = 2
        self.assertEqual(self.diff(), [{"id": CHOICE, "reasons": ["distractor"]}])
        self.answers[CHOICE]["distractors"]["a"] = 0
        self.answers[CHOICE]["distractors"]["d"] = 3
        self.assertEqual(self.diff(), [{"id": CHOICE, "reasons": ["distractor"]}])
        self.answers[CHOICE]["distractors"]["d"] = 1
        self.assertEqual(self.diff(), [])

    def test_rating_of_something_that_is_not_a_wrong_option_fails(self):
        self.answers[CHOICE]["distractors"]["b"] = 0  # the correct option
        self.assertEqual(self.diff(), [{"id": CHOICE, "reasons": ["distractor"]}])
        del self.answers[CHOICE]["distractors"]["b"]
        self.answers[CHOICE]["distractors"]["z"] = 0  # no such option
        self.assertEqual(self.diff(), [{"id": CHOICE, "reasons": ["distractor"]}])
        del self.answers[CHOICE]["distractors"]["z"]
        self.answers[NUMERIC]["distractors"]["a"] = 0  # a typed-number question has no options
        self.assertEqual(self.diff(), [{"id": NUMERIC, "reasons": ["distractor"]}])

    def test_missing_entry_fails(self):
        del self.answers[NUMERIC]
        self.assertEqual(self.diff(), [{"id": NUMERIC, "reasons": ["missing"]}])
        self.answers[NUMERIC] = None
        self.assertEqual(self.diff(), [{"id": NUMERIC, "reasons": ["missing"]}])

    def test_an_empty_object_counts_its_missing_fields(self):
        self.answers[NUMERIC] = {}
        self.assertEqual(self.diff(), [{"id": NUMERIC, "reasons": ["answer", "check", "unique"]}])

    def test_questions_of_other_grades_are_not_looked_at(self):
        missing = [{"id": q["id"], "reasons": ["missing"]} for q in grade_questions(self.corpus, 2)]
        self.assertEqual(blind.diff(self.corpus, 2, self.answers), missing)
        answers = clean_answers(self.corpus, 2)
        answers[NUMERIC] = None  # an entry for a question of another grade is ignored
        self.assertEqual(blind.diff(self.corpus, 2, answers), [])

    def test_every_reason_of_one_question_is_reported_in_order(self):
        self.answers[CHOICE].update(answer="a", check="kvadrat", unique=False, assumptions=["nešto"], distractors={"a": 3, "c": 0, "d": 0})
        self.assertEqual(self.diff(), [{"id": CHOICE, "reasons": ["answer", "check", "unique", "assumptions", "distractor"]}])

    def test_failures_keep_the_file_order_of_the_questions(self):
        for question_id in ("mat-geometrijski-oblici-q2", "mat-brojevi-do-10-q4", NUMERIC):
            self.answers[question_id]["unique"] = False
        self.assertEqual([failure["id"] for failure in self.diff()], ["mat-brojevi-do-10-q4", NUMERIC, "mat-geometrijski-oblici-q2"])

    def test_diff_changes_nothing(self):
        self.answers[NUMERIC]["unique"] = False
        before = copy.deepcopy((self.corpus.question_list, self.answers))
        self.assertEqual([failure["id"] for failure in self.diff()], [NUMERIC])
        self.assertEqual((self.corpus.question_list, self.answers), before)


class EveryDistractorRatedTest(unittest.TestCase):
    def setUp(self):
        self.corpus = helpers.fixture_corpus()
        self.question = helpers.question(helpers.fixture_raw(), "mat-poredjenje-do-100-q3")
        self.choices = self.corpus.questions["mat-poredjenje-do-100-q3"]["choices"]

    def codes(self, mutate):
        answers = clean_answers(self.corpus, 2)
        mutate(answers["mat-poredjenje-do-100-q3"])
        return blind.diff(self.corpus, 2, answers)

    def test_a_clean_sheet_passes(self):
        self.assertEqual(self.codes(lambda entry: None), [])

    def test_a_wrong_option_without_a_rating_fails(self):
        wrong = [choice["id"] for choice in self.choices if choice["id"] != "b"]
        failures = self.codes(lambda entry: entry["distractors"].pop(wrong[0]))
        self.assertEqual([failure["reasons"] for failure in failures], [["distractor"]])

    def test_no_ratings_at_all_fails(self):
        failures = self.codes(lambda entry: entry.update({"distractors": {}}))
        self.assertEqual([failure["reasons"] for failure in failures], [["distractor"]])

    def test_a_numeric_question_needs_no_ratings(self):
        answers = clean_answers(self.corpus, 2)
        answers["mat-poredjenje-do-100-q1"]["distractors"] = {}
        self.assertEqual(blind.diff(self.corpus, 2, answers), [])
