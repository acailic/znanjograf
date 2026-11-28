"""Text lint L2–L5 and L7 on the fixture, and the helper that lists words missing from the digraph lexicon."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from zg import paths
from zg.corpus import Corpus, RawCorpus
from zg.issues import Issues
from zg.lint import text
from zg.translit import rules
from tests import helpers

ROOT = Path(__file__).resolve().parent.parent
TOPIC = "mat-brojevi-do-10"
QUESTION = "mat-brojevi-do-10-q1"
TOPICS_FILE = "data/math/g1/topics.json"
G1_QUESTIONS = "data/math/g1/questions.json"


def lint(raw: RawCorpus) -> Issues:
    issues = Issues()
    text.run(Corpus.from_raw("math", raw), issues)
    return issues


# Entries the lexicon tests take out of the fixture, which classifies every word it uses.
UNCLASSIFIED = ("sabiranje", "poređenje", "manje")
UNCLASSIFIED_IN_ORDER = ["manje", "poređenje", "sabiranje"]


def raw_without(*words: str) -> RawCorpus:
    """The fixture with ``words`` removed from its digraph lexicon."""
    raw = helpers.fixture_raw()
    for word in words:
        del raw.lexicon[word]
    return raw


def only(issues: Issues, code: str) -> list:
    return [issue for issue in issues if issue.code == code]


def prose(length: int) -> str:
    """Harmless running text of exactly ``length`` characters."""
    unit = "Koliki je zbir brojeva 12 i 15? "
    return (unit * (length // len(unit) + 1))[:length]


TOPIC_TEXTS = {
    "name": "Brojevi  do 10",
    "summary": "Brojevi  do 10 i njihov redosled.",
    "unit": "Brojevi  i figure",
    "root_reason": "Ovo je pojam  od koga polaze svi ostali.",
}


def set_topic_field(field):
    def mutate(raw):
        helpers.topic(raw, TOPIC)[field] = TOPIC_TEXTS[field]

    return mutate


def set_mastery(raw):
    helpers.topic(raw, TOPIC)["mastery"][1] = "imenuje broj  koji dolazi pre i posle datog broja"


def set_prompt(raw):
    helpers.question(raw, "mat-oduzimanje-do-100-q1")["prompt"] = "Koliko  je $58 - 23$?"


def set_explanation(raw):
    helpers.question(raw, "mat-brojevi-do-10-q1")["explanation"] = "Posle broja 5  dolazi broj 4."


def set_choice(raw):
    helpers.question(raw, "mat-geometrijski-oblici-q1")["choices"][0]["text"] = "kvadrat  i krug"


def set_figure(raw):
    helpers.question(raw, "mat-geometrijski-oblici-q1")["figure"] = {"kind": "dots", "alt": "Sedam  tačaka u nizu."}


def set_outcome(raw):
    raw.editions["g1-2026"]["outcomes"][0]["text"] = "broji,  čita i piše brojeve do 10"


def set_outcome_unit(raw):
    raw.editions["g1-2026"]["outcomes"][0]["unit"] = "Brojevi  i sabiranje"


def set_edge(raw):
    raw.edges[1][0]["reason"] = "Sabiranje  brojeva do 10 zahteva poznavanje samih brojeva do 10."


class LintTextBaselineTest(unittest.TestCase):
    def test_clean_fixture_has_no_issues(self):
        self.assertEqual(list(lint(helpers.fixture_raw())), [])

    def test_gate_changes_nothing(self):
        raw = helpers.fixture_raw()
        before = copy.deepcopy(raw.__dict__)
        corpus = Corpus.from_raw("math", raw)
        lexicon = dict(corpus.lexicon)
        text.run(corpus, Issues())
        self.assertEqual(raw.__dict__, before)
        self.assertEqual(corpus.lexicon, lexicon)

    def test_repository_lexicon_classifies_every_fixture_digraph_word(self):
        corpus = Corpus.from_raw("math", helpers.fixture_raw())
        on_disk = json.loads(paths.DIGRAPHS_FILE.read_text(encoding="utf-8"))
        self.assertEqual(set(text.missing_from_lexicon(corpus)) - set(on_disk), set())

    def test_repository_lexicon_agrees_with_the_default_rule_on_the_fixture(self):
        corpus = Corpus.from_raw("math", helpers.fixture_raw())
        on_disk = json.loads(paths.DIGRAPHS_FILE.read_text(encoding="utf-8"))
        for field in text.iter_text_fields(corpus):
            self.assertEqual(rules.to_cyrillic(field.text, on_disk), rules.to_cyrillic(field.text), field.where)

    def test_every_text_field_is_visited(self):
        cases = [
            ("topic name", set_topic_field("name"), f"{TOPIC}.name", TOPICS_FILE),
            ("topic summary", set_topic_field("summary"), f"{TOPIC}.summary", TOPICS_FILE),
            ("topic unit", set_topic_field("unit"), f"{TOPIC}.unit", TOPICS_FILE),
            ("topic root_reason", set_topic_field("root_reason"), f"{TOPIC}.root_reason", TOPICS_FILE),
            ("topic mastery item", set_mastery, f"{TOPIC}.mastery[1]", TOPICS_FILE),
            ("question prompt", set_prompt, "mat-oduzimanje-do-100-q1.prompt", "data/math/g2/questions.json"),
            ("question explanation", set_explanation, f"{QUESTION}.explanation", G1_QUESTIONS),
            ("choice text", set_choice, "mat-geometrijski-oblici-q1.choices[0].text", G1_QUESTIONS),
            ("figure alt", set_figure, "mat-geometrijski-oblici-q1.figure.alt", G1_QUESTIONS),
            ("outcome text", set_outcome, "g1-2026-001.text", "data/curriculum/math/g1-2026.json"),
            ("outcome unit", set_outcome_unit, "g1-2026-001.unit", "data/curriculum/math/g1-2026.json"),
            ("edge reason", set_edge, "mat-sabiranje-do-10 -> mat-brojevi-do-10.reason", "data/math/g1/edges.json"),
        ]
        for name, mutate, where, path in cases:
            with self.subTest(field=name):
                raw = helpers.fixture_raw()
                mutate(raw)
                self.assertEqual([(i.path, i.where) for i in only(lint(raw), "L4-orthography")], [(path, where)])

    def test_messages_are_serbian_latin(self):
        raw = helpers.fixture_raw()
        helpers.question(raw, QUESTION)["prompt"] = "Koliko je 3.5, a koliko 15%?"
        helpers.topic(raw, TOPIC)["name"] = "Brojevi  do 10"
        for issue in lint(raw):
            self.assertNotRegex(issue.message, "[Ѐ-ӿ]", issue)
            self.assertEqual(issue.code, issue.code.encode("ascii").decode())


class FoldedWordsTest(unittest.TestCase):
    def setUp(self):
        self.raw = helpers.fixture_raw()
        self.raw.lexicon["množenje"] = "digraph"

    def test_word_without_diacritics_beside_the_same_word_with_them(self):
        helpers.topic(self.raw, TOPIC)["summary"] = "Množenje je ponovljeno sabiranje, a mnozenje u glavi ide brže."
        issues = only(lint(self.raw), "L2-folded")
        self.assertEqual(len(issues), 1)
        self.assertEqual((issues[0].path, issues[0].where), (TOPICS_FILE, f"{TOPIC}.summary"))
        self.assertIn("mnozenje", issues[0].message)
        self.assertIn("množenje", issues[0].message.lower())

    def test_found_whatever_the_field_case_or_order(self):
        # the word without diacritics comes first, in another record and in capitals
        helpers.topic(self.raw, TOPIC)["summary"] = "RESENJE je broj 7."
        helpers.question(self.raw, QUESTION)["explanation"] = "Posle broja 7 dolazi rešenje."
        issues = only(lint(self.raw), "L2-folded")
        self.assertEqual([(i.path, i.where) for i in issues], [(TOPICS_FILE, f"{TOPIC}.summary")])
        self.assertIn("RESENJE", issues[0].message)
        self.assertIn("rešenje", issues[0].message)

    def test_words_inside_math_and_units_are_not_collected(self):
        helpers.question(self.raw, QUESTION)["prompt"] = "Koliko je $mnozenje$? Množenje je u formuli."
        self.assertEqual(only(lint(self.raw), "L2-folded"), [])

    def test_only_the_diacritic_free_twin_is_reported(self):
        helpers.question(self.raw, QUESTION)["explanation"] = "Rešenje je rešenje, a ne resenje."
        issues = only(lint(self.raw), "L2-folded")
        self.assertEqual(len(issues), 1)
        self.assertTrue(issues[0].message.startswith("reč „resenje“"), issues[0].message)

    def test_words_that_are_right_as_they_stand_are_left_alone(self):
        # Each word of the set stands in the fixture beside the word it folds to.
        # „sto“ (the table, the hundred) folds like „što“ and „mesa“ (of meat) like „meša“: neither lacks a letter
        helpers.topic(self.raw, TOPIC)["summary"] = "Učenik zna šta i što radi i kako meša boje. Zbir je suma brojeva, a šuma je puna drveta."
        helpers.question(self.raw, QUESTION)["explanation"] = "Na stolu ima sto kockica i komad mesa."
        # ``zapisu`` (of a notation) is not ``zapišu``, ``sume`` (of sums) is not ``šume`` (of forests)
        helpers.question(self.raw, QUESTION)["prompt"] = "U decimalnom zapisu broja učenici zapišu cifru 5 jednom; sume su zbirovi, a šume su velike."
        self.assertEqual(only(lint(self.raw), "L2-folded"), [])
        # Without its exception every such word is reported, and only that word: the check above tests something.
        for word in sorted(text._LEGITIMATE):
            without = text._LEGITIMATE - {word}
            with self.subTest(word=word), mock.patch.object(text, "_LEGITIMATE", without):
                issues = only(lint(self.raw), "L2-folded")
                self.assertEqual(len(issues), 1, [issue.message for issue in issues])
                self.assertTrue(issues[0].message.startswith(f"reč „{word}“"), issues[0].message)


class DigraphWordsTest(unittest.TestCase):
    def setUp(self):
        self.raw = helpers.fixture_raw()

    def test_word_with_digraph_missing_from_the_lexicon(self):
        helpers.question(self.raw, QUESTION)["explanation"] = "Reč džungla znači veliku šumu."
        issues = only(lint(self.raw), "L3-digraph")
        self.assertEqual([(i.path, i.where) for i in issues], [(G1_QUESTIONS, f"{QUESTION}.explanation")])
        self.assertIn("džungla", issues[0].message)
        self.assertIn("dž", issues[0].message)
        self.assertIn("digraphs.json", issues[0].message)

    def test_lj_nj_and_dž_all_need_classification(self):
        for word, digraph in (("biljka", "lj"), ("konj", "nj"), ("džungla", "dž")):
            with self.subTest(word=word):
                raw = helpers.fixture_raw()
                helpers.question(raw, QUESTION)["explanation"] = f"Reč {word} je ovde nova."
                issues = only(lint(raw), "L3-digraph")
                self.assertEqual(len(issues), 1)
                self.assertIn(f"„{digraph}“", issues[0].message)

    def test_classified_word_passes(self):
        helpers.question(self.raw, QUESTION)["explanation"] = "Reč džungla znači veliku šumu."
        self.raw.lexicon["džungla"] = "digraph"
        self.assertEqual(only(lint(self.raw), "L3-digraph"), [])

    def test_lookup_ignores_case(self):
        helpers.question(self.raw, QUESTION)["explanation"] = "Džungla je velika šuma, a džungla i prašuma."
        self.raw.lexicon["džungla"] = "split:d|ž"
        self.assertEqual(only(lint(self.raw), "L3-digraph"), [])

    def test_word_inside_math_is_not_checked(self):
        helpers.question(self.raw, QUESTION)["explanation"] = "Napiši $džungla$ u svesci."
        self.assertEqual(only(lint(self.raw), "L3-digraph"), [])

    def test_dj_needs_no_lexicon(self):
        helpers.question(self.raw, QUESTION)["explanation"] = "Odjek je čujan, a podjednak znači jednak."
        self.assertEqual(only(lint(self.raw), "L3-digraph"), [])


class OrthographyTest(unittest.TestCase):
    def setUp(self):
        self.raw = helpers.fixture_raw()

    def test_decimal_point_between_digits(self):
        helpers.question(self.raw, QUESTION)["prompt"] = "Koliko je 3.5 + 1.2?"
        issues = only(lint(self.raw), "L4-orthography")
        self.assertEqual(len(issues), 2)
        self.assertIn("3,5", issues[0].message)
        self.assertIn("{,}", issues[0].message)

    def test_decimal_point_inside_math_url_or_tag_is_not_prose(self):
        for prompt in ("Koliko je $3.5 + 1.2$?", "Vidi https://primer.rs/v3.5/stavka.", '<a href="/v3.5">stranica</a>'):
            with self.subTest(prompt=prompt):
                raw = helpers.fixture_raw()
                helpers.question(raw, QUESTION)["prompt"] = prompt
                self.assertEqual(only(lint(raw), "L4-orthography"), [])

    def test_decimal_comma_and_space_separated_thousands_are_right(self):
        helpers.question(self.raw, QUESTION)["prompt"] = "Koliko je 3,5 + 1 000,25?"
        self.assertEqual(only(lint(self.raw), "L4-orthography"), [])

    def test_percent_without_space(self):
        helpers.question(self.raw, QUESTION)["prompt"] = "Koliko je 15% od 200?"
        issues = only(lint(self.raw), "L4-orthography")
        self.assertEqual(len(issues), 1)
        self.assertIn("15 %", issues[0].message)

    def test_percent_with_space_or_in_math(self):
        for prompt in ("Koliko je 15 % od 200?", "Koliko je $15\\,\\%$ od 200?"):
            with self.subTest(prompt=prompt):
                raw = helpers.fixture_raw()
                helpers.question(raw, QUESTION)["prompt"] = prompt
                self.assertEqual(only(lint(raw), "L4-orthography"), [])

    def test_two_spaces_in_a_row(self):
        helpers.question(self.raw, QUESTION)["prompt"] = "Koliko  je 7?"
        issues = only(lint(self.raw), "L4-orthography")
        self.assertEqual(len(issues), 1)

    def test_space_before_punctuation(self):
        helpers.question(self.raw, QUESTION)["prompt"] = "Koliko je 7 , a koliko 5 ?"
        issues = only(lint(self.raw), "L4-orthography")
        self.assertEqual(len(issues), 2)
        self.assertIn("„,“", issues[0].message)
        self.assertIn("„?“", issues[1].message)

    def test_ellipsis_after_a_space_is_not_a_full_stop(self):
        helpers.question(self.raw, QUESTION)["prompt"] = "Nastavi niz: 2, 4, 6, ..."
        self.assertEqual(only(lint(self.raw), "L4-orthography"), [])

    def test_cyrillic_letter_in_the_latin_source(self):
        helpers.topic(self.raw, TOPIC)["name"] = "Sabiranje до 20"
        helpers.question(self.raw, QUESTION)["prompt"] = "Koliko je $а$?"
        issues = only(lint(self.raw), "L4-orthography")
        self.assertEqual([(i.where, i.path) for i in issues], [(f"{TOPIC}.name", TOPICS_FILE), (f"{QUESTION}.prompt", G1_QUESTIONS)])
        self.assertIn("д", issues[0].message)


class LengthTest(unittest.TestCase):
    def test_prompt_limit_follows_the_grade(self):
        for grade, limit in ((1, 200), (2, 200), (3, 300), (4, 300), (5, 400), (8, 400)):
            with self.subTest(grade=grade):
                raw = helpers.fixture_raw()
                helpers.topic(raw, TOPIC)["grade"] = grade
                helpers.question(raw, QUESTION)["prompt"] = prose(limit)
                self.assertEqual(only(lint(raw), "L5-length"), [])
                helpers.question(raw, QUESTION)["prompt"] = prose(limit + 1)
                issues = only(lint(raw), "L5-length")
                self.assertEqual([(i.path, i.where) for i in issues], [(G1_QUESTIONS, f"{QUESTION}.prompt")])
                self.assertIn(str(limit), issues[0].message)

    def test_explanation_limit(self):
        raw = helpers.fixture_raw()
        helpers.question(raw, QUESTION)["explanation"] = prose(400)
        self.assertEqual(only(lint(raw), "L5-length"), [])
        helpers.question(raw, QUESTION)["explanation"] = prose(401)
        issues = only(lint(raw), "L5-length")
        self.assertEqual([(i.path, i.where) for i in issues], [(G1_QUESTIONS, f"{QUESTION}.explanation")])
        self.assertIn("400", issues[0].message)

    def test_choice_text_has_no_limit(self):
        raw = helpers.fixture_raw()
        helpers.question(raw, "mat-geometrijski-oblici-q1")["choices"][0]["text"] = prose(450)
        self.assertEqual(only(lint(raw), "L5-length"), [])


class MixedScriptTest(unittest.TestCase):
    def check(self, cyrillic):
        issues = Issues()
        text.check_mixed_script(cyrillic, "gde", "putanja", issues)
        return issues

    def test_latin_word_left_in_cyrillic_text(self):
        issues = self.check("Ово је tekst на ћирилици, а veće је погрешно.")
        self.assertEqual(issues.codes(), {"L7-mixed-script"})
        self.assertEqual([(i.path, i.where) for i in issues], [("putanja", "gde"), ("putanja", "gde")])
        self.assertIn("tekst", issues[0].message)
        self.assertIn("veće", issues[1].message)

    def test_pure_cyrillic_is_clean(self):
        self.assertEqual(list(self.check("Ово је текст на ћирилици.")), [])

    def test_mixed_word_and_latin_word(self):
        issues = self.check("Kућа је црвена, а kuća плава.")
        self.assertEqual(len(issues), 2)
        self.assertIn("Kућа", issues[0].message)
        self.assertIn("kuća", issues[1].message)

    def test_one_issue_per_word(self):
        self.assertEqual(len(self.check("tekst tekst, па rec")), 2)

    def test_words_that_stay_latin_by_rule_are_clean(self):
        self.assertEqual(list(self.check("Ознаке HTML, YouTube и x остају латиничне.")), [])

    def test_math_and_units_are_protected(self):
        self.assertEqual(list(self.check("Дужина износи $x$ и 5 cm, види www.sajt.rs.")), [])

    def test_latin_text_alone_is_reported_word_by_word(self):
        self.assertEqual(len(self.check("Koliko je")), 2)

    def test_run_reports_mixed_script_of_the_built_text(self):
        raw = helpers.fixture_raw()
        helpers.question(raw, QUESTION)["explanation"] = "Broj 6 je kuванog broja."
        issues = only(lint(raw), "L7-mixed-script")
        self.assertEqual([(i.path, i.where) for i in issues], [(G1_QUESTIONS, f"{QUESTION}.explanation")])
        self.assertIn("kuванog", issues[0].message)


class LexiconHelpersTest(unittest.TestCase):
    def test_fixture_classifies_every_digraph_word_it_uses(self):
        self.assertEqual(text.missing_from_lexicon(Corpus.from_raw("math", helpers.fixture_raw())), [])

    def test_missing_words_are_lowercase_distinct_and_in_alphabet_order(self):
        missing = text.missing_from_lexicon(Corpus.from_raw("math", raw_without(*UNCLASSIFIED)))
        self.assertEqual(missing, UNCLASSIFIED_IN_ORDER)
        self.assertIn("sabiranje", missing)
        self.assertNotIn("manji", missing)
        self.assertNotIn("injekcija", missing)
        self.assertEqual(missing, [word.lower() for word in missing])

    def test_classifying_the_missing_words_empties_the_list(self):
        raw = raw_without(*UNCLASSIFIED)
        corpus = Corpus.from_raw("math", raw)
        self.assertEqual(text.missing_from_lexicon(corpus), UNCLASSIFIED_IN_ORDER)
        raw.lexicon.update({word: "digraph" for word in UNCLASSIFIED})
        self.assertEqual(text.missing_from_lexicon(Corpus.from_raw("math", raw)), [])

    def test_split_entry_counts_as_classified(self):
        raw = helpers.fixture_raw()
        helpers.question(raw, QUESTION)["explanation"] = "Dobio je injekciju u ruku."
        self.assertEqual(text.missing_from_lexicon(Corpus.from_raw("math", raw)), ["injekciju"])
        raw.lexicon["injekciju"] = "split:n|j"
        self.assertEqual(text.missing_from_lexicon(Corpus.from_raw("math", raw)), [])


class AddDigraphsToolTest(unittest.TestCase):
    def run_tool(self, root: Path):
        script = ROOT / "tools" / "add-digraphs.py"
        return subprocess.run([sys.executable, str(script), "--root", str(root)], capture_output=True, text=True, cwd=ROOT)

    def test_lists_unclassified_words_one_per_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = helpers.write_corpus(Path(tmp), raw_without(*UNCLASSIFIED))
            result = self.run_tool(root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "manje\npoređenje\nsabiranje\n")
        lines = result.stdout.splitlines()
        self.assertIn("sabiranje", lines)
        self.assertNotIn("manji", lines)
        self.assertEqual(len(lines), len(set(lines)))
        self.assertEqual(lines, sorted(lines, key=rules.collation_key))

    def test_silent_when_every_word_is_classified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = helpers.write_corpus(Path(tmp), helpers.fixture_raw())
            result = self.run_tool(root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_broken_corpus_is_reported_on_stderr(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "data").mkdir()
            (Path(tmp) / "data" / "math").mkdir()
            (Path(tmp) / "data" / "math" / "meta.json").write_text("{", encoding="utf-8")
            result = self.run_tool(Path(tmp))
        self.assertEqual(result.returncode, 1)
        self.assertIn("meta.json", result.stderr)


if __name__ == "__main__":
    unittest.main()
