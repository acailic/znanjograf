"""The Cyrillic mirror must be right for everything a reader sees (review of 2026-11-26)."""

import copy
import tempfile
import unittest
from pathlib import Path

from zg import build, jsonio
from zg.corpus import Corpus
from zg.issues import Issues
from zg.lint import text
from zg.translit import rules
from tests import helpers


class MirrorBuildTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "repo"
        self.raw = helpers.fixture_raw()
        self.raw.questions[1][0]["figure"] = {"kind": "numberline", "min": 0, "max": 10, "marks": [3], "unit": "cm",
                                              "alt": "Brojevna prava od nule do deset sa oznakom na broju tri."}
        helpers.write_corpus(self.root, self.raw)
        jsonio.dump({"mat-brojevi-do-10": {"name": "Milana Marković", "role": "nastavnica matematike", "date": "2026-11-26", "note": "Sve je u redu."}},
                    self.root / "data" / "review" / "teachers.json")
        self.out = self.root / "_site"
        build.build_site(self.root, self.out, Path(self.tmp.name) / "no-site")

    def bundle(self, rel):
        return jsonio.load(self.out / rel)

    def test_a_teacher_review_is_cyrillic_in_the_mirror(self):
        latin = self.bundle("podaci/g1.lat.json")["topics"]["mat-brojevi-do-10"]["review"]
        cyrillic = self.bundle("cir/podaci/g1.cyr.json")["topics"]["mat-brojevi-do-10"]["review"]
        self.assertEqual(latin["name"], "Milana Marković")
        self.assertEqual(cyrillic["name"], "Милана Марковић")
        self.assertEqual(cyrillic["role"], "наставница математике")
        self.assertEqual(cyrillic["date"], latin["date"])

    def test_a_figure_unit_stays_a_symbol_while_a_theme_name_is_transliterated(self):
        figure = self.bundle("cir/podaci/g1.cyr.json")["questions"]["mat-brojevi-do-10-q1"]["figure"]
        self.assertEqual(figure["unit"], "cm")
        self.assertEqual(figure["alt"], "Бројевна права од нуле до десет са ознаком на броју три.")
        self.assertEqual(self.bundle("cir/podaci/index.cyr.json")["topics"][0]["unit"], "Бројеви")
        self.assertEqual(self.bundle("cir/podaci/index.cyr.json")["areas"], ["numbers", "geometry", "data"])

    def test_the_mirror_of_the_fixture_is_clean(self):
        issues = Issues()
        checked = text.run_built(issues, self.out)
        self.assertEqual(list(issues), [])
        self.assertGreater(checked, 100)

    def test_a_serbian_word_left_in_latin_in_the_mirror_is_reported(self):
        file = self.out / "cir" / "podaci" / "index.cyr.json"
        index = jsonio.load(file)
        index["topics"][0]["name"] = "Brojevi do deset"
        jsonio.dump(index, file)
        issues = Issues()
        text.run_built(issues, self.out)
        self.assertEqual({(issue.path, issue.code) for issue in issues}, {("cir/podaci/index.cyr.json", "L7-mixed-script")})
        self.assertEqual(len(issues), 3)  # "Brojevi", "do" and "deset"
        self.assertTrue(any("Brojevi" in issue.message for issue in issues))

    def test_machine_values_in_the_mirror_are_not_mistaken_for_leaks(self):
        file = self.out / "cir" / "podaci" / "g1.cyr.json"
        bundle = jsonio.load(file)
        question = bundle["questions"]["mat-poredjenje-do-100-q3"] = bundle["questions"]["mat-brojevi-do-10-q1"]
        question.update({"type": "choice", "answer": "b", "points_to": {"a": "mat-brojevi-do-10"},
                         "choices": [{"id": "a", "text": "$<$"}, {"id": "b", "text": "$>$"}]})
        jsonio.dump(bundle, file)
        issues = Issues()
        text.run_built(issues, self.out)
        self.assertEqual(list(issues), [])

    def test_nothing_is_checked_when_nothing_is_built(self):
        self.assertEqual(text.run_built(Issues(), Path(self.tmp.name) / "no-site"), 0)

    def test_lint_runs_the_mirror_check_only_for_the_repository_itself(self):
        issues = Issues()
        text.run(Corpus.from_raw("math", self.raw), issues)  # an in-memory corpus has no site
        self.assertEqual([issue.code for issue in issues if issue.path.startswith("cir/")], [])


class UnitSymbolsAnywhereTest(unittest.TestCase):
    def test_multi_letter_symbols_stay_latin_without_a_number_in_front(self):
        self.assertEqual(rules.to_cyrillic("Jedinica je cm, a masa ide u kg."), "Јединица је cm, а маса иде у kg.")

    def test_short_symbols_are_units_only_after_a_number(self):
        self.assertEqual(rules.to_cyrillic("Dužina je 5 m, a masa 3 kg."), "Дужина је 5 m, а маса 3 kg.")
        self.assertEqual(rules.to_cyrillic("a", {}), "а")  # the conjunction is a Serbian word


class NearDuplicateNamesTest(unittest.TestCase):
    def codes(self, second_id, second_name):
        raw = helpers.fixture_raw()
        topic = helpers.topic(raw, second_id)
        topic["name"] = second_name
        issues = Issues()
        text.run(Corpus.from_raw("math", raw), issues)
        return [issue.where for issue in issues if issue.code == "L6-near-duplicate"]

    def test_a_name_differing_by_one_letter_is_a_duplicate(self):
        raw = helpers.fixture_raw()
        helpers.topic(raw, "mat-sabiranje-do-10")["name"] = "Množenje razlomaka"
        helpers.topic(raw, "mat-sabiranje-do-20")["name"] = "Mnozenje razlomaka"
        issues = Issues()
        text.run(Corpus.from_raw("math", raw), issues)
        self.assertEqual([issue.where for issue in issues if issue.code == "L6-near-duplicate"], ["mat-sabiranje-do-20"])

    def test_ranges_that_differ_by_number_are_different_topics(self):
        self.assertEqual(self.codes("mat-sabiranje-do-20", "Sabiranje do 30"), [])

    def test_the_same_name_twice_is_a_duplicate(self):
        self.assertEqual(self.codes("mat-sabiranje-do-20", "Sabiranje do 100"), ["mat-sabiranje-do-20"])

    def test_unrelated_names_are_left_alone(self):
        self.assertEqual(self.codes("mat-geometrijski-oblici", "Geometrijski oblici"), [])


class MirrorCheckDetailsTest(unittest.TestCase):
    def check(self, rel, content):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            file = out / "cir" / rel
            file.parent.mkdir(parents=True)
            file.write_text(content, encoding="utf-8")
            issues = Issues()
            text.run_built(issues, out)
            return [(issue.where, issue.message) for issue in issues]

    def test_a_placeholder_name_is_not_a_leak(self):
        self.assertEqual(self.check("js/strings.js", 'export const strings = {\n  grade: "${n}. разред",\n  id: "Тема „${id}“.",\n};\n'), [])

    def test_a_real_word_in_the_cyrillic_strings_file_is_a_leak(self):
        found = self.check("js/strings.js", 'export const strings = {\n  title: "Znanjograf",\n};\n')
        self.assertEqual(len(found), 1)
        self.assertIn("Znanjograf", found[0][1])

    def test_a_key_written_in_quotes_is_not_checked(self):
        self.assertEqual(self.check("js/strings.js", 'export const strings = {\n  "role": "улога",\n};\n'), [])

    def test_the_title_of_a_mirrored_page_is_checked(self):
        self.assertEqual(self.check("mapa/index.html", "<title>Знањограф — мапа знања</title><noscript>Укључи JavaScript.</noscript>"), [])
        found = self.check("mapa/index.html", "<title>Znanjograf — mapa znanja</title>")
        self.assertEqual(len(found), 3)  # "Znanjograf", "mapa", "znanja"

    def test_a_broken_mirror_file_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "cir" / "podaci").mkdir(parents=True)
            (Path(tmp) / "cir" / "podaci" / "g1.cyr.json").write_text("{", encoding="utf-8")
            issues = Issues()
            text.run_built(issues, Path(tmp))
            self.assertEqual([issue.code for issue in issues], ["V1-json"])
