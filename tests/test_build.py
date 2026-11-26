import re
import tempfile
import unittest
from pathlib import Path

from zg import build, jsonio
from tests import helpers

PAGE = """<!doctype html>
<html lang="sr-Latn">
<head><meta charset="utf-8"><title>Znanjograf — mapa znanja</title>
<link rel="stylesheet" href="../css/zg.css">
<script type="module" src="../js/pages/map.js"></script>
</head>
<body data-pismo="lat" data-podaci="../podaci/">
<noscript>Znanjograf radi samo sa uključenim JavaScriptom.</noscript>
</body></html>
"""
PAGE_JS = 'import { strings } from "../strings.js";\nexport const label = strings.title;\n'
STRINGS_JS = (
    "export const strings = {\n"
    '  title: "Znanjograf",\n'
    '  steps: ["Izaberi temu", "Odgovori na pitanja"],\n'
    '  "quoted-key": "Ključ ostaje",\n'
    "  greeting: `Zdravo, ${name}!`,\n"
    "};\n"
)
MATH = re.compile(r"\$[^$]*\$")


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.raw = helpers.fixture_raw()
        helpers.write_corpus(self.root, self.raw)
        self.site = self.root / "site-src"
        (self.site / "mapa").mkdir(parents=True)
        (self.site / "mapa" / "index.html").write_text(PAGE, encoding="utf-8")
        (self.site / "js" / "pages").mkdir(parents=True)
        (self.site / "js" / "strings.js").write_text(STRINGS_JS, encoding="utf-8")
        (self.site / "js" / "pages" / "map.js").write_text(PAGE_JS, encoding="utf-8")
        self.out = self.root / "_site"

    def tearDown(self):
        self.tmp.cleanup()

    def build(self):
        return build.build_site(self.root, self.out, self.site)

    # ----- files ---------------------------------------------------------------------

    def test_writes_every_bundle_in_both_trees(self):
        manifest = self.build()
        for name in (
            "manifest.json", "mapa/index.html", "js/strings.js", "js/pages/map.js",
            "podaci/index.lat.json", "podaci/g1.lat.json", "podaci/g2.lat.json", "podaci/ishodi/g1-2026.lat.json",
            "cir/mapa/index.html", "cir/js/strings.js",
            "cir/podaci/index.cyr.json", "cir/podaci/g1.cyr.json", "cir/podaci/ishodi/g2-2026.cyr.json",
        ):
            self.assertTrue((self.out / name).exists(), name)
        self.assertFalse((self.out / "podaci" / "index.cyr.json").exists())
        self.assertEqual(set(manifest), {"data", "script", "built"})

    # ----- index ---------------------------------------------------------------------

    def test_index_carries_topics_edges_and_counts(self):
        self.build()
        index = jsonio.load(self.out / "podaci" / "index.lat.json")
        self.assertEqual(index["counts"], {"topics": 8, "edges": 8, "questions": 32})
        self.assertEqual(index["topics"][1]["name"], "Sabiranje do 10")
        self.assertEqual(index["topics"][1]["area"], "numbers")
        self.assertEqual(index["units"], {"1": ["Brojevi", "Geometrija"], "2": ["Brojevi"]})
        self.assertIn(["mat-poredjenje-do-100", "mat-sabiranje-do-10", "soft"], index["edges"])
        self.assertEqual(index["aliases"], {"mat-brojevi": ["mat-brojevi-do-10"]})

    def test_cyrillic_index_changes_only_text(self):
        self.build()
        latin = jsonio.load(self.out / "podaci" / "index.lat.json")
        cyrillic = jsonio.load(self.out / "cir" / "podaci" / "index.cyr.json")
        self.assertEqual(cyrillic["topics"][1]["name"], "Сабирање до 10")
        self.assertEqual(cyrillic["topics"][1]["id"], "mat-sabiranje-do-10")
        self.assertEqual(cyrillic["topics"][1]["area"], "numbers")
        self.assertEqual(cyrillic["topics"][1]["unit"], "Бројеви")
        self.assertEqual(cyrillic["edges"], latin["edges"])
        self.assertEqual(cyrillic["aliases"], latin["aliases"])
        self.assertEqual(cyrillic["name"], "Математика")

    # ----- grade bundles ---------------------------------------------------------------

    def test_math_spans_are_identical_in_both_scripts(self):
        self.build()
        latin = jsonio.load(self.out / "podaci" / "g2.lat.json")["questions"]
        cyrillic = jsonio.load(self.out / "cir" / "podaci" / "g2.cyr.json")["questions"]
        self.assertEqual(set(latin), set(cyrillic))
        for question_id, question in latin.items():
            self.assertEqual(MATH.findall(question["prompt"]), MATH.findall(cyrillic[question_id]["prompt"]), question_id)
        self.assertEqual(cyrillic["mat-poredjenje-do-100-q3"]["prompt"], "Који знак треба уписати: $56$ ____ $65$?")
        self.assertEqual(cyrillic["mat-poredjenje-do-100-q3"]["answer"], "b")
        self.assertEqual(cyrillic["mat-poredjenje-do-100-q3"]["points_to"], {"a": "mat-brojevi-do-10"})

    def test_curriculum_ids_survive_transliteration(self):
        self.build()
        topics = jsonio.load(self.out / "cir" / "podaci" / "g1.cyr.json")["topics"]
        self.assertEqual(
            topics["mat-brojevi-do-10"]["curriculum"][0],
            {"edition": "g1-2026", "outcome": "g1-2026-001", "match": "exact"},
        )
        self.assertEqual(topics["mat-brojevi-do-10"]["mastery"][0], "редом наброји бројеве од 1 до 10")

    def test_answer_rational_for_a_fraction_answer(self):
        question = helpers.question(self.raw, "mat-poredjenje-do-100-q4")
        question["answer"], question["check"] = "3/4", "(/ 3 4)"
        helpers.write_corpus(self.root, self.raw)
        self.build()
        bundle = jsonio.load(self.out / "podaci" / "g2.lat.json")["questions"]
        self.assertEqual(bundle["mat-poredjenje-do-100-q4"]["answerRational"], ["3", "4"])
        self.assertEqual(bundle["mat-poredjenje-do-100-q1"]["answerRational"], ["43", "1"])
        self.assertNotIn("answerRational", bundle["mat-poredjenje-do-100-q3"])

    def test_outcomes_bundle_keeps_codes_and_ids(self):
        self.build()
        outcomes = jsonio.load(self.out / "cir" / "podaci" / "ishodi" / "g1-2026.cyr.json")
        self.assertEqual(outcomes["outcomes"][0]["id"], "g1-2026-001")
        self.assertEqual(outcomes["outcomes"][0]["area"], "numbers")
        self.assertEqual(outcomes["outcomes"][0]["text"], "броји, чита и пише бројеве до 10")

    # ----- the Cyrillic mirror ----------------------------------------------------------

    def test_mirror_html_is_transliterated_and_stays_relative(self):
        self.build()
        html = (self.out / "cir" / "mapa" / "index.html").read_text(encoding="utf-8")
        self.assertIn('data-pismo="cyr"', html)
        self.assertIn('lang="sr-Cyrl"', html)
        self.assertIn("<title>Знањограф — мапа знања</title>", html)
        self.assertIn("Знањограф ради само са укљученим JavaScriptom.", html)
        self.assertIn('href="../css/zg.css"', html)
        self.assertIn('src="../js/pages/map.js"', html)

    def test_mirror_strings_are_transliterated_but_not_code(self):
        self.build()
        strings = (self.out / "cir" / "js" / "strings.js").read_text(encoding="utf-8")
        self.assertIn('title: "Знањограф"', strings)
        self.assertIn('steps: ["Изабери тему", "Одговори на питања"]', strings)
        self.assertIn('"quoted-key": "Кључ остаје"', strings)
        self.assertIn("greeting: `Здраво, ${name}!`", strings)
        self.assertIn("export const strings", strings)
        untouched = (self.out / "cir" / "js" / "pages" / "map.js").read_text(encoding="utf-8")
        self.assertEqual(untouched, PAGE_JS)

    # ----- determinism -------------------------------------------------------------------

    def test_second_build_changes_nothing(self):
        first = self.build()
        second = self.build()
        self.assertEqual(first["data"], second["data"])
        self.assertEqual(first["script"], second["script"])
        self.assertEqual(build.check_site(self.root, self.out, self.site), [])

    def test_check_site_reports_an_edit(self):
        self.build()
        helpers.topic(self.raw, "mat-brojevi-do-10")["name"] = "Brojevi do deset"
        helpers.write_corpus(self.root, self.raw)
        differences = build.check_site(self.root, self.out, self.site)
        self.assertTrue(any(line.startswith("podaci/index.lat.json") for line in differences), differences)
        self.assertTrue(any(line.startswith("cir/podaci/index.cyr.json") for line in differences), differences)

    def test_check_site_on_a_missing_build(self):
        self.assertEqual(len(build.check_site(self.root, self.out, self.site)), 1)
