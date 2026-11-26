"""Transliteration between the two Serbian scripts: protected spans, letters, digraphs, fold, collation, golden corpus."""

import json
import unittest
from pathlib import Path

from zg.translit import protect, rules

GOLDEN = Path(__file__).resolve().parent / "fixtures" / "translit-golden.json"
ALPHABET = "абвгдђежзијклљмнњопрстћуфхцчџш"
PLAN_UNITS = {"mm", "cm", "dm", "km", "m", "kg", "g", "mg", "t", "l", "ml", "dl", "h", "min", "s", "°C", "km/h", "m/s", "m²", "m³", "a", "ha", "din"}


def protected_spans(text):
    return [segment for segment, is_protected in protect.split_protected(text) if is_protected]


class SplitProtectedTest(unittest.TestCase):
    CASES = [
        "", "Mila ima 8 kuvanica", "$3{,}5$ cm", "$", "$$", "$a$", "$$x$$", "$a$$b$", "$ $", "5$ ili 3$",
        "Ima $5 i $3$ kvasaca", "<b>x</b>", "<!DOCTYPE html>", "<!-- kraj -->", "a &amp; b &#160; c",
        "https://primer.rs/a_(b)", "5 cm", "5  cm", "5cm", "12 cm²", "16 m²", "25 °C", "u °C", "$5$ cm", "$x$ a",
        "5 m/s i 60 km/h", "x", "a m s", "5 dinara", "2 minute", "$$5$$ cm", "5\u00a0cm",
    ]

    def test_segments_join_back_into_the_text(self):
        for text in self.CASES:
            with self.subTest(text=text):
                self.assertEqual("".join(segment for segment, _ in protect.split_protected(text)), text)

    def test_segments_are_never_empty(self):
        for text in self.CASES:
            for segment, is_protected in protect.split_protected(text):
                self.assertTrue(segment, text)

    def test_empty_text_has_no_segments(self):
        self.assertEqual(protect.split_protected(""), [])

    def test_math_span_is_protected_and_the_words_around_it_are_not(self):
        self.assertEqual(
            protect.split_protected("Mila ima $8$ kuvanica"),
            [("Mila ima ", False), ("$8$", True), (" kuvanica", False)],
        )

    def test_display_math_is_one_span(self):
        self.assertEqual(protected_spans("$$x + y$$ i $z$"), ["$$x + y$$", "$z$"])

    def test_unmatched_dollar_is_ordinary_text(self):
        self.assertEqual(protect.split_protected("Cena je 5$"), [("Cena je 5$", False)])

    def test_only_the_unit_is_protected_never_the_number(self):
        self.assertEqual(protect.split_protected("5 cm"), [("5 ", False), ("cm", True)])
        self.assertEqual(protect.split_protected("3kg"), [("3", False), ("kg", True)])
        self.assertEqual(protect.split_protected("5\u00a0cm"), [("5\u00a0", False), ("cm", True)])

    def test_unit_after_a_number_written_in_math(self):
        self.assertEqual(protected_spans("$3{,}5$ cm"), ["$3{,}5$", "cm"])
        self.assertEqual(protected_spans("$$5$$ cm"), ["$$5$$", "cm"])

    def test_every_unit_symbol_of_the_plan_is_protected_after_a_number(self):
        for unit in sorted(PLAN_UNITS - {"°C"}):
            with self.subTest(unit=unit):
                self.assertEqual(protected_spans(f"iznosi 25 {unit}."), [unit])

    def test_bare_unit_letters_are_ordinary_words(self):
        text = "Strana a je duža, a m i s nisu brojevi."
        self.assertEqual(protect.split_protected(text), [(text, False)])

    def test_letter_after_a_number_is_a_unit(self):
        self.assertEqual(protected_spans("Plac ima 5 a."), ["a"])

    def test_letter_after_a_variable_is_a_word(self):
        self.assertEqual(protected_spans("$x$ a ne $y$"), ["$x$", "$y$"])
        self.assertEqual(protected_spans("$5$ cm, a $5$ m"), ["$5$", "cm", "$5$", "m"])

    def test_two_spaces_break_the_unit(self):
        self.assertEqual(protected_spans("5  cm"), [])

    def test_word_that_starts_like_a_unit_is_a_word(self):
        self.assertEqual(protected_spans("2 minute, 5 dinara, 3 sekunde i 12 sati"), [])

    def test_unit_starts_with_at_least_a_digit(self):
        for text in ("pet cm", "x cm", "(5) cm", "5.cm", "5 - cm"):
            with self.subTest(text=text):
                self.assertEqual(protected_spans(text), [])

    def test_url_ends_before_closing_punctuation(self):
        self.assertEqual(
            protect.split_protected("Vidi https://primer.rs/stranica."),
            [("Vidi ", False), ("https://primer.rs/stranica", True), (".", False)],
        )
        self.assertEqual(protected_spans("(www.sajt.rs) i dalje"), ["www.sajt.rs"])
        self.assertEqual(protected_spans("https://primer.rs/a_(b)"), ["https://primer.rs/a_(b)"])

    def test_url_never_crosses_a_tag_or_a_quote(self):
        self.assertEqual(protected_spans('www.sajt.rs<b>i</b> "dalje"'), ["www.sajt.rs", "<b>", "</b>"])

    def test_markup_is_protected_and_the_text_between_tags_is_not(self):
        self.assertEqual(
            protect.split_protected("<b>duplo</b>"),
            [("<b>", True), ("duplo", False), ("</b>", True)],
        )
        self.assertEqual(protected_spans('<a href="https://x.rs?t=1">tekst</a>'), ['<a href="https://x.rs?t=1">', "</a>"])
        self.assertEqual(protected_spans("&nbsp;i &#160; <!DOCTYPE html> <!-- kraj -->"), ["&nbsp;", "&#160;", "<!DOCTYPE html>", "<!-- kraj -->"])

    def test_comparison_in_prose_is_not_a_tag(self):
        self.assertEqual(protected_spans("5 < 7 i 3 > 2"), [])

    def test_degree_celsius_is_always_a_unit(self):
        self.assertEqual(protected_spans("25 °C i u °C"), ["°C", "°C"])

    def test_superscript_areas_keep_their_unit(self):
        self.assertEqual(protected_spans("12 cm² i 16 m²"), ["cm", "m²"])

    def test_unit_symbols_are_exactly_the_ones_planned(self):
        self.assertEqual(set(protect.UNIT_SYMBOLS), PLAN_UNITS)

    def test_unit_pattern_matches_a_whole_token(self):
        self.assertEqual([m.group() for m in protect.UNIT_PATTERN.finditer("cm kg m² dinara minimalno sam")], ["cm", "kg", "m²"])


class ToCyrillicTest(unittest.TestCase):
    def test_letters(self):
        self.assertEqual(rules.to_cyrillic("Mila ima 8 kuvanica"), "Мила има 8 куваница")

    def test_every_single_letter_in_both_cases(self):
        # one letter at a time: a word of several capitals is an acronym and stays Latin
        for latin, cyrillic in zip("abcčćdđefghijklmnoprsštuvzž", "абцчћдђефгхијклмнопрсштувзж"):
            with self.subTest(latin=latin):
                self.assertEqual(rules.to_cyrillic(latin), cyrillic)
                self.assertEqual(rules.to_cyrillic(latin.upper()), cyrillic.upper())

    def test_whole_alphabet_written_as_a_word(self):
        self.assertEqual(rules.to_cyrillic("abcčćdđefghijklmnoprsštuvzž"), "абцчћдђефгхијклмнопрсштувзж")

    def test_every_digraph_letter_round_trips_in_both_cases(self):
        for latin, cyrillic in (("lj", "љ"), ("nj", "њ"), ("dž", "џ")):
            with self.subTest(latin=latin):
                self.assertEqual(rules.to_cyrillic(latin), cyrillic)
                self.assertEqual(rules.to_cyrillic(latin.capitalize()), cyrillic.upper())
                self.assertEqual(rules.to_latin(cyrillic), latin)
                self.assertEqual(rules.to_latin(cyrillic.upper()), latin.capitalize())

    def test_protected_spans_are_untouched(self):
        for text in ("$3{,}5$ cm", "$x + y = 7$", "60 km/h", "25 °C", "16 m²", "www.matematika.rs", "<b>", "5 kg", "150 din", "2 ha"):
            with self.subTest(text=text):
                self.assertEqual(rules.to_cyrillic(text), text)

    def test_tags_stay_and_the_text_between_them_is_transliterated(self):
        self.assertEqual(rules.to_cyrillic("<b>duplo</b> veće"), "<b>дупло</b> веће")
        self.assertEqual(rules.to_cyrillic("Vidi &nbsp;stranicu."), "Види &nbsp;страницу.")

    def test_url_keeps_a_serbian_looking_path(self):
        self.assertEqual(rules.to_cyrillic("Više na https://primer.rs/najnovije."), "Више на https://primer.rs/najnovije.")

    def test_unit_stays_latin_but_the_same_letters_in_a_word_do_not(self):
        self.assertEqual(rules.to_cyrillic("Stranica je 5 cm, a dužina 3 m."), "Страница је 5 cm, а дужина 3 m.")
        self.assertEqual(rules.to_cyrillic("Oznaka m znači metar, a s je sekunda."), "Ознака м значи метар, а с је секунда.")

    def test_words_with_foreign_letters_stay(self):
        self.assertEqual(
            rules.to_cyrillic("Vrednost x je 5, a q i w nisu brojevi."),
            "Вредност x је 5, а q и w нису бројеви.",
        )

    def test_acronyms_stay(self):
        self.assertEqual(rules.to_cyrillic("Oznake HTML i NASA ostaju"), "Ознаке HTML и NASA остају")
        self.assertEqual(rules.to_cyrillic("Trougao ABC ima tri ugla"), "Троугао ABC има три угла")

    def test_single_capital_is_transliterated(self):
        self.assertEqual(rules.to_cyrillic("Tačka A je centar"), "Тачка А је центар")
        self.assertEqual(rules.to_cyrillic("B"), "Б")

    def test_capital_inside_a_word_keeps_it_latin(self):
        self.assertEqual(rules.to_cyrillic("Uključi JavaScript u pregledaču"), "Укључи JavaScript у прегледачу")
        self.assertEqual(rules.to_cyrillic("Radim sa JavaScriptom, YouTube i PowerPoint"), "Радим са JavaScriptom, YouTube и PowerPoint")

    def test_digraphs_by_default(self):
        self.assertEqual(rules.to_cyrillic("ljubav, njuška, džungla"), "љубав, њушка, џунгла")
        self.assertEqual(rules.to_cyrillic("Ljubav, Njuška, Džungla"), "Љубав, Њушка, Џунгла")

    def test_dj_is_never_a_digraph(self):
        self.assertEqual(rules.to_cyrillic("odjek je čujan, podjednak"), "одјек је чујан, подједнак")

    def test_lexicon_splits_the_pair_and_the_rest_keeps_the_rule(self):
        lexicon = {"injekcija": "split:n|j", "nadživeti": "split:d|ž", "ljubav": "digraph"}
        self.assertEqual(rules.to_cyrillic("injekcija", lexicon), "инјекција")
        self.assertEqual(rules.to_cyrillic("Injekcija", lexicon), "Инјекција")
        self.assertEqual(rules.to_cyrillic("injekcijom", lexicon), "ињекцијом")  # only the listed word is split
        self.assertEqual(rules.to_cyrillic("nadživeti", lexicon), "надживети")
        self.assertEqual(rules.to_cyrillic("ljubav", lexicon), "љубав")

    def test_without_the_lexicon_the_default_rule_applies(self):
        self.assertEqual(rules.to_cyrillic("injekcija"), "ињекција")
        self.assertEqual(rules.to_cyrillic("injekcija", {}), "ињекција")

    def test_unknown_or_broken_lexicon_entry_falls_back_to_the_rule(self):
        for entry in ("digraph", "", "split:n|x", "split:nn|j", "whatever"):
            with self.subTest(entry=entry):
                self.assertEqual(rules.to_cyrillic("injekcija", {"injekcija": entry}), "ињекција")

    def test_cyrillic_text_is_left_alone(self):
        once = rules.to_cyrillic("Sabiranje do 20")
        self.assertEqual(once, "Сабирање до 20")
        self.assertEqual(rules.to_cyrillic(once), once)

    def test_word_mixing_scripts_is_left_alone(self):
        self.assertEqual(rules.to_cyrillic("kuванica"), "kuванica")

    def test_needs_lexicon(self):
        for word in ("injekcija", "ljubav", "džungla", "DŽUNGla", "sabiranje", "Njihov", "manji"):
            self.assertTrue(rules.needs_lexicon(word), word)
        for word in ("odjek", "veće", "matematika", "najveći", "đ", "ž", "a", "podjednak"):
            self.assertFalse(rules.needs_lexicon(word), word)

    def test_is_transliterated(self):
        for word in ("sabiranje", "Sabiranje", "A", "a", "Đak", "Ljubav"):
            self.assertTrue(rules.is_transliterated(word), word)
        for word in ("HTML", "JavaScript", "JavaScriptom", "YouTube", "x", "q", "множ", "kuванica"):
            self.assertFalse(rules.is_transliterated(word), word)


class ToLatinTest(unittest.TestCase):
    def test_inverse(self):
        self.assertEqual(rules.to_latin("множење"), "množenje")

    def test_every_letter(self):
        self.assertEqual(rules.to_latin("абцчћдђефгхијклмнопрсштувзж"), "abcčćdđefghijklmnoprsštuvzž")
        self.assertEqual(rules.to_latin("АБЦЧЋДЂЕФГХИЈКЛМНОПРСШТУВЗЖ"), "ABCČĆDĐEFGHIJKLMNOPRSŠTUVZŽ")

    def test_digraph_letters(self):
        self.assertEqual(rules.to_latin("Љубав, Њушка, Џунгла"), "Ljubav, Njuška, Džungla")
        self.assertEqual(rules.to_latin("ЉУБАВ"), "LjUBAV")

    def test_latin_text_is_untouched(self):
        self.assertEqual(rules.to_latin("Sabiranje do 20, 5 cm, $x$"), "Sabiranje do 20, 5 cm, $x$")


class FoldTest(unittest.TestCase):
    def test_fold(self):
        self.assertEqual(rules.fold("Množenje"), "mnozenje")

    def test_fold_drops_diacritics_and_everything_that_is_not_a_letter_or_digit(self):
        self.assertEqual(rules.fold("Č, Ć, Š, Ž i Đ!"), "ccszidj")
        self.assertEqual(rules.fold("Sabiranje do 20!"), "sabiranjedo20")
        self.assertEqual(rules.fold("$+$ — ."), "")

    def test_fold_keeps_lj_and_nj_and_flattens_dž_and_đ(self):
        self.assertEqual(rules.fold("ljubav, njuška, džungla, đak"), "ljubavnjuskadzungladjak")

    def test_fold_ignores_script_and_case(self):
        self.assertEqual(rules.fold("множење"), rules.fold("množenje"))
        self.assertEqual(rules.fold("Љубав"), rules.fold("ljubav"))
        self.assertEqual(rules.fold("Џунгла"), "dzungla")


class CollationKeyTest(unittest.TestCase):
    def test_digraphs_are_single_letters_in_alphabet_order(self):
        self.assertLess(rules.collation_key("lj"), rules.collation_key("m"))
        self.assertLess(rules.collation_key("nj"), rules.collation_key("o"))

    def test_serbian_alphabet_order(self):
        words = ["šuma", "k", "zora", "casa", "đak", "džungla", "i", "žirafa", "ćup", "eka", "j", "čamac", "njiva", "obala", "ljubav", "luk"]
        self.assertEqual(
            sorted(words, key=rules.collation_key),
            ["đak", "eka", "žirafa", "zora", "i", "j", "k", "luk", "ljubav", "njiva", "obala", "ćup", "casa", "čamac", "džungla", "šuma"],
        )

    def test_every_letter_precedes_the_next_one(self):
        for first, second in zip(ALPHABET, ALPHABET[1:]):
            with self.subTest(first=first):
                self.assertLess(rules.collation_key(first), rules.collation_key(second))

    def test_ignores_case_and_script(self):
        self.assertEqual(rules.collation_key("Mila"), rules.collation_key("мила"))
        self.assertEqual(rules.collation_key("Mila"), rules.collation_key("MILA"))
        self.assertEqual(rules.collation_key("Ljubav"), rules.collation_key("Љубав"))

    def test_other_characters_sort_after_the_letters(self):
        self.assertLess(rules.collation_key("ш"), rules.collation_key("1"))
        self.assertEqual(rules.collation_key("1 a"), (len(ALPHABET), len(ALPHABET), 0))
        self.assertEqual(rules.collation_key(""), ())


class TranslitObjTest(unittest.TestCase):
    def test_deep_values_are_transliterated_and_keys_are_not(self):
        obj = {
            "name": "Sabiranje", "mastery": ["rešava zadatak", "proveri"], "grade": 1, "ok": True, "none": None,
            "figure": {"alt": "krug i kvadrat", "count": 5}, "empty": [],
        }
        self.assertEqual(
            rules.translit_obj(obj),
            {
                "name": "Сабирање", "mastery": ["решава задатак", "провери"], "grade": 1, "ok": True, "none": None,
                "figure": {"alt": "круг и квадрат", "count": 5}, "empty": [],
            },
        )
        self.assertEqual(obj["name"], "Sabiranje")

    def test_string_and_scalars(self):
        self.assertEqual(rules.translit_obj("Sabiranje"), "Сабирање")
        self.assertEqual(rules.translit_obj(5), 5)
        self.assertIsNone(rules.translit_obj(None))

    def test_lexicon_is_handed_to_the_function(self):
        self.assertEqual(rules.translit_obj(["injekcija"], lexicon={"injekcija": "split:n|j"}), ["инјекција"])
        self.assertEqual(rules.translit_obj(["injekcija"]), ["ињекција"])

    def test_other_function(self):
        self.assertEqual(rules.translit_obj({"a": "множење"}, rules.to_latin), {"a": "množenje"})


class GoldenCorpusTest(unittest.TestCase):
    def setUp(self):
        self.pairs = json.loads(GOLDEN.read_text(encoding="utf-8"))

    def test_shape(self):
        self.assertIsInstance(self.pairs, list)
        for pair in self.pairs:
            self.assertEqual(len(pair), 2, pair)
            self.assertTrue(all(isinstance(side, str) for side in pair), pair)

    def test_at_least_forty_real_sentences(self):
        self.assertGreaterEqual(len(self.pairs), 40)
        latin = [pair[0] for pair in self.pairs]
        self.assertEqual(len(set(latin)), len(latin))
        for sentence in latin:
            self.assertGreaterEqual(len(sentence.split()), 3, sentence)

    def test_every_cyrillic_letter_is_covered(self):
        seen = "".join(cyrillic for _, cyrillic in self.pairs)
        for letter in ALPHABET + ALPHABET.upper():
            self.assertIn(letter, seen, letter)

    def test_sentences_keep_math_and_units(self):
        latin = [pair[0] for pair in self.pairs]
        self.assertGreaterEqual(sum("$" in sentence for sentence in latin), 10)
        self.assertGreaterEqual(sum(" cm" in sentence for sentence in latin), 5)

    def test_latin_to_cyrillic(self):
        for latin, cyrillic in self.pairs:
            with self.subTest(latin=latin):
                self.assertEqual(rules.to_cyrillic(latin), cyrillic)

    def test_cyrillic_to_latin_and_round_trip(self):
        for latin, cyrillic in self.pairs:
            with self.subTest(latin=latin):
                self.assertEqual(rules.to_latin(cyrillic), latin)
                self.assertEqual(rules.to_latin(rules.to_cyrillic(latin)), latin)


if __name__ == "__main__":
    unittest.main()
