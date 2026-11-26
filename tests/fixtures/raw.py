"""The fixture corpus: a tiny but complete mathematics subject, valid by definition.

Two grades, eight topics, eight edges, thirty-two questions and two curriculum
editions. Every gate must return zero issues on it; tests copy it, break one
thing and assert the rule code that reports it.

These are hand-written examples for tests only. Real content lives in ``data/``.
"""

from __future__ import annotations


def topic(topic_id, grade, area, unit, kind, name, summary, mastery, curriculum, root_reason=None):
    record = {
        "id": topic_id,
        "grade": grade,
        "area": area,
        "unit": unit,
        "kind": kind,
        "name": name,
        "summary": summary,
        "mastery": mastery,
        "curriculum": [{"edition": edition, "outcome": outcome, "match": match} for edition, outcome, match in curriculum],
    }
    if root_reason is not None:
        record["root_reason"] = root_reason
    return record


def edge(topic_id, requires, strength, reason):
    return {"topic": topic_id, "requires": requires, "strength": strength, "reason": reason}


def numeric(question_id, topic_id, level, prompt, answer, check, explanation):
    return {
        "id": question_id,
        "topic": topic_id,
        "level": level,
        "type": "numeric",
        "prompt": prompt,
        "answer": answer,
        "check": check,
        "explanation": explanation,
    }


def choice(question_id, topic_id, level, prompt, options, answer, check, explanation, points_to=None):
    record = {
        "id": question_id,
        "topic": topic_id,
        "level": level,
        "type": "choice",
        "prompt": prompt,
        "choices": [{"id": key, "text": text} for key, text in options],
        "answer": answer,
        "check": check,
        "explanation": explanation,
    }
    if points_to:
        record["points_to"] = points_to
    return record


GRADES = [1, 2]

TOPICS = {
    1: [
        topic(
            "mat-brojevi-do-10", 1, "numbers", "Brojevi", "concept", "Brojevi do 10",
            "Prepoznavanje, čitanje i pisanje brojeva od 1 do 10 i njihov redosled.",
            ["redom nabroji brojeve od 1 do 10", "imenuje broj koji dolazi pre i posle datog broja"],
            [("g1-2026", "g1-2026-001", "exact"), ("g1-2026", "g1-2026-005", "exact")],
            "Ovo je pojam od koga polaze svi ostali: bez brojeva do 10 nema sabiranja.",
        ),
        topic(
            "mat-sabiranje-do-10", 1, "numbers", "Brojevi", "procedure", "Sabiranje do 10",
            "Sabiranje dva jednocifrena broja sa zbirom do 10.",
            ["sabira dva broja sa zbirom do 10", "rešava jednostavan zadatak sa jednim sabiranjem"],
            [("g1-2026", "g1-2026-002", "exact")],
        ),
        topic(
            "mat-sabiranje-do-20", 1, "numbers", "Brojevi", "procedure", "Sabiranje do 20",
            "Sabiranje brojeva sa zbirom do 20, uključujući prelaz preko desetice.",
            ["sabira dva broja sa zbirom do 20", "prelazi preko desetice pri sabiranju"],
            [("g1-2026", "g1-2026-003", "exact")],
        ),
        topic(
            "mat-geometrijski-oblici", 1, "geometry", "Geometrija", "concept", "Geometrijski oblici",
            "Prepoznavanje i imenovanje osnovnih ravnih figura u okolini.",
            ["imenuje krug, kvadrat, trougao i pravougaonik", "razlikuje figure po broju strana"],
            [("g1-2026", "g1-2026-004", "exact")],
            "Prepoznavanje oblika ne polazi ni od kog drugog pojma u ovom skupu.",
        ),
    ],
    2: [
        topic(
            "mat-sabiranje-do-100", 2, "numbers", "Brojevi", "procedure", "Sabiranje do 100",
            "Sabiranje dvocifrenih brojeva u okviru prve stotine.",
            ["sabira dva dvocifrena broja", "rešava zadatak iz svakodnevnog života sa sabiranjem do 100"],
            [("g2-2026", "g2-2026-001", "exact")],
        ),
        topic(
            "mat-poredjenje-do-100", 2, "numbers", "Brojevi", "concept", "Poređenje brojeva do 100",
            "Poređenje i uređivanje brojeva do 100 pomoću znakova $<$, $>$ i $=$.",
            ["upoređuje dva broja do 100", "uređuje tri broja od najmanjeg do najvećeg"],
            [("g2-2026", "g2-2026-002", "exact"), ("g2-2026", "g2-2026-005", "partial")],
        ),
        topic(
            "mat-oduzimanje-do-100", 2, "numbers", "Brojevi", "procedure", "Oduzimanje do 100",
            "Oduzimanje dvocifrenih brojeva u okviru prve stotine.",
            ["oduzima dva dvocifrena broja", "rešava zadatak sa oduzimanjem do 100"],
            [("g2-2026", "g2-2026-003", "exact"), ("g2-2026", "g2-2026-006", "partial")],
        ),
        topic(
            "mat-zadaci-sa-sabiranjem", 2, "numbers", "Brojevi", "problem", "Zadaci sa sabiranjem",
            "Rešavanje tekstualnih zadataka sa jednim ili više sabiranja.",
            ["prepoznaje koji su podaci u zadatku potrebni", "rešava zadatak u više koraka i proverava rezultat"],
            [("g2-2026", "g2-2026-004", "exact")],
        ),
    ],
}

EDGES = {
    1: [
        edge("mat-sabiranje-do-10", "mat-brojevi-do-10", "hard", "Sabiranje brojeva do 10 zahteva poznavanje samih brojeva do 10."),
        edge("mat-sabiranje-do-20", "mat-sabiranje-do-10", "hard", "Sabiranje do 20 nastavlja na sabiranje do 10 i koristi ga bez prelaza."),
    ],
    2: [
        edge("mat-sabiranje-do-100", "mat-sabiranje-do-20", "hard", "Pisano sabiranje dvocifrenih brojeva koristi usmeno sabiranje do 20."),
        edge("mat-poredjenje-do-100", "mat-brojevi-do-10", "hard", "Poređenje dvocifrenih brojeva polazi od poređenja jednocifrenih."),
        edge("mat-poredjenje-do-100", "mat-sabiranje-do-10", "soft", "Računanje zbirova pomaže pri proceni koji je broj veći, ali nije uslov."),
        edge("mat-oduzimanje-do-100", "mat-sabiranje-do-100", "hard", "Oduzimanje se proverava sabiranjem i koristi iste pisane postupke."),
        edge("mat-zadaci-sa-sabiranjem", "mat-sabiranje-do-100", "hard", "Svaki zadatak ovog tipa sadrži bar jedno sabiranje do 100."),
        edge("mat-zadaci-sa-sabiranjem", "mat-poredjenje-do-100", "soft", "Poređenje pomaže pri proveri da li je rezultat razuman."),
    ],
}

QUESTIONS = {
    1: [
        numeric("mat-brojevi-do-10-q1", "mat-brojevi-do-10", "basic", "Koji broj dolazi posle broja $6$?", "7", "7", "Posle broja 6 dolazi broj 7."),
        numeric("mat-brojevi-do-10-q2", "mat-brojevi-do-10", "basic", "Koji broj dolazi pre broja $5$?", "4", "4", "Pre broja 5 dolazi broj 4."),
        choice(
            "mat-brojevi-do-10-q3", "mat-brojevi-do-10", "standard", "Koji je najveći broj: $6$, $9$, $3$ ili $8$?",
            [("a", "$6$"), ("b", "$9$"), ("c", "$3$"), ("d", "$8$")], "b", "9", "Od brojeva 6, 9, 3 i 8 najveći je 9.",
        ),
        numeric("mat-brojevi-do-10-q4", "mat-brojevi-do-10", "standard", "U nizu $4$, $5$, ____, $7$ koji broj nedostaje?", "6", "6", "Između 5 i 7 dolazi 6."),
        numeric("mat-sabiranje-do-10-q1", "mat-sabiranje-do-10", "basic", "Koliko je $3 + 4$?", "7", "(+ 3 4)", "3 i 4 zajedno daju 7."),
        numeric("mat-sabiranje-do-10-q2", "mat-sabiranje-do-10", "basic", "Koliko je $2 + 6$?", "8", "(+ 2 6)", "2 i 6 zajedno daju 8."),
        numeric("mat-sabiranje-do-10-q3", "mat-sabiranje-do-10", "standard", "Mila ima $5$ kuvanica, a Pera $2$. Koliko kuvanica imaju zajedno?", "7", "(+ 5 2)", "5 + 2 = 7 kuvanica."),
        numeric("mat-sabiranje-do-10-q4", "mat-sabiranje-do-10", "standard", "Koliko je $2 + 3 + 4$?", "9", "(+ 2 3 4)", "2 + 3 = 5, pa 5 + 4 = 9."),
        numeric("mat-sabiranje-do-20-q1", "mat-sabiranje-do-20", "basic", "Koliko je $9 + 5$?", "14", "(+ 9 5)", "9 + 1 = 10, pa još 4: 14."),
        numeric("mat-sabiranje-do-20-q2", "mat-sabiranje-do-20", "basic", "Koliko je $7 + 6$?", "13", "(+ 7 6)", "7 + 3 = 10, pa još 3: 13."),
        numeric("mat-sabiranje-do-20-q3", "mat-sabiranje-do-20", "standard", "Mila ima $8$ kuvanica i kupi još $7$. Koliko kuvanica sada ima?", "15", "(+ 8 7)", "8 + 2 = 10, pa još 5: 15."),
        numeric("mat-sabiranje-do-20-q4", "mat-sabiranje-do-20", "standard", "Koliko je $6 + 5 + 4$?", "15", "(+ 6 5 4)", "6 + 5 = 11, pa 11 + 4 = 15."),
        choice(
            "mat-geometrijski-oblici-q1", "mat-geometrijski-oblici", "basic", "Koja figura ima tri strane?",
            [("a", "kvadrat"), ("b", "trougao"), ("c", "krug"), ("d", "pravougaonik")], "b", "trougao", "Trougao ima tri strane.",
        ),
        choice(
            "mat-geometrijski-oblici-q2", "mat-geometrijski-oblici", "basic", "Koja figura nema uglove?",
            [("a", "krug"), ("b", "kvadrat"), ("c", "trougao"), ("d", "pravougaonik")], "a", "krug", "Krug nema ni jedan ugao.",
        ),
        choice(
            "mat-geometrijski-oblici-q3", "mat-geometrijski-oblici", "standard", "Koliko strana ima kvadrat?",
            [("a", "$3$"), ("b", "$5$"), ("c", "$4$"), ("d", "$6$")], "c", "4", "Kvadrat ima četiri jednake strane.",
        ),
        choice(
            "mat-geometrijski-oblici-q4", "mat-geometrijski-oblici", "standard", "Koja figura ima četiri jednake strane?",
            [("a", "trougao"), ("b", "pravougaonik"), ("c", "krug"), ("d", "kvadrat")], "d", "kvadrat",
            "Kvadrat ima četiri jednake strane; pravougaonik ima samo naspramne strane jednake.",
        ),
    ],
    2: [
        numeric("mat-sabiranje-do-100-q1", "mat-sabiranje-do-100", "basic", "Koliko je $23 + 45$?", "68", "(+ 23 45)", "20 + 40 = 60, 3 + 5 = 8, ukupno 68."),
        numeric("mat-sabiranje-do-100-q2", "mat-sabiranje-do-100", "basic", "Koliko je $40 + 37$?", "77", "(+ 40 37)", "40 + 37 = 77."),
        numeric("mat-sabiranje-do-100-q3", "mat-sabiranje-do-100", "standard", "Koliko je $36 + 28$?", "64", "(+ 36 28)", "36 + 20 = 56, pa 56 + 8 = 64."),
        numeric(
            "mat-sabiranje-do-100-q4", "mat-sabiranje-do-100", "standard",
            "U autobusu su $26$ putnika. Na sledećoj stanici ušlo je još $19$. Koliko putnika sada ima u autobusu?",
            "45", "(+ 26 19)", "26 + 19 = 45 putnika.",
        ),
        numeric("mat-poredjenje-do-100-q1", "mat-poredjenje-do-100", "basic", "Koji je broj veći: $34$ ili $43$? Upiši taj broj.", "43", "43", "43 ima više desetica od 34."),
        numeric("mat-poredjenje-do-100-q2", "mat-poredjenje-do-100", "basic", "Koji je broj manji: $89$ ili $98$? Upiši taj broj.", "89", "89", "89 ima manje desetica od 98."),
        choice(
            "mat-poredjenje-do-100-q3", "mat-poredjenje-do-100", "standard", "Koji znak treba upisati: $56$ ____ $65$?",
            [("a", "$>$"), ("b", "$<$"), ("c", "$=$")], "b", "<", "56 je manje od 65.",
            points_to={"a": "mat-brojevi-do-10"},
        ),
        numeric("mat-poredjenje-do-100-q4", "mat-poredjenje-do-100", "standard", "Poredaj od najmanjeg: $71$, $17$, $70$. Koji broj je u sredini?", "70", "70", "Redom: 17, 70, 71."),
        numeric("mat-oduzimanje-do-100-q1", "mat-oduzimanje-do-100", "basic", "Koliko je $58 - 23$?", "35", "(- 58 23)", "50 - 20 = 30, 8 - 3 = 5, ukupno 35."),
        numeric("mat-oduzimanje-do-100-q2", "mat-oduzimanje-do-100", "basic", "Koliko je $90 - 40$?", "50", "(- 90 40)", "90 - 40 = 50."),
        numeric("mat-oduzimanje-do-100-q3", "mat-oduzimanje-do-100", "standard", "Koliko je $72 - 45$?", "27", "(- 72 45)", "72 - 40 = 32, pa 32 - 5 = 27."),
        numeric(
            "mat-oduzimanje-do-100-q4", "mat-oduzimanje-do-100", "standard",
            "Mila je imala $62$ dinara i potrošila $27$. Koliko dinara joj je ostalo?",
            "35", "(- 62 27)", "62 - 27 = 35 dinara.",
        ),
        numeric("mat-zadaci-sa-sabiranjem-q1", "mat-zadaci-sa-sabiranjem", "basic", "Mila ima $24$ sličice, a Pera $15$. Koliko sličica imaju zajedno?", "39", "(+ 24 15)", "24 + 15 = 39 sličica."),
        numeric("mat-zadaci-sa-sabiranjem-q2", "mat-zadaci-sa-sabiranjem", "basic", "U kutiji su $33$ crvene i $26$ plavih kuglica. Koliko kuglica ima u kutiji?", "59", "(+ 33 26)", "33 + 26 = 59 kuglica."),
        numeric(
            "mat-zadaci-sa-sabiranjem-q3", "mat-zadaci-sa-sabiranjem", "standard",
            "Mila je pročitala $18$ stranica ujutru, $22$ posle podne i $10$ uveče. Koliko stranica je pročitala tog dana?",
            "50", "(+ 18 22 10)", "18 + 22 = 40, pa 40 + 10 = 50 stranica.",
        ),
        numeric(
            "mat-zadaci-sa-sabiranjem-q4", "mat-zadaci-sa-sabiranjem", "standard",
            "Pera je imao $35$ dinara. Dobio je $20$ dinara od bake i $15$ od dede. Koliko dinara sada ima?",
            "70", "(+ 35 20 15)", "35 + 20 = 55, pa 55 + 15 = 70 dinara.",
        ),
    ],
}

EDITIONS = {
    "g1-2026": {
        "edition": "g1-2026",
        "grade": 1,
        "applies_from": "2026/27",
        "themes": [
            {"name": "Brojevi", "area": "numbers", "hours": 146, "content": ["Brojevi do 10", "Sabiranje do 20"], "page": 12},
            {"name": "Geometrija", "area": "geometry", "hours": 27, "content": ["Geometrijske figure"], "page": 14},
        ],
        "outcomes": [
            {"id": "g1-2026-001", "text": "broji, čita i piše brojeve do 10", "page": 12, "area": "numbers", "unit": "Brojevi"},
            {"id": "g1-2026-002", "text": "sabira dva jednocifrena broja", "page": 12, "area": "numbers", "unit": "Brojevi"},
            {"id": "g1-2026-003", "text": "sabira i oduzima do 20", "page": 12, "area": "numbers", "unit": "Brojevi"},
            {"id": "g1-2026-004", "text": "imenuje geometrijske figure: krug, kvadrat, trougao i pravougaonik", "page": 14, "area": "geometry", "unit": "Geometrija"},
            {"id": "g1-2026-005", "text": "poredi brojeve do 10", "page": 12, "area": "numbers", "unit": "Brojevi"},
        ],
    },
    "g2-2026": {
        "edition": "g2-2026",
        "grade": 2,
        "applies_from": "2026/27",
        "themes": [
            {"name": "Brojevi", "area": "numbers", "hours": 150, "content": ["Sabiranje i oduzimanje do 100", "Poređenje brojeva"], "page": 20},
        ],
        "outcomes": [
            {"id": "g2-2026-001", "text": "sabira brojeve do 100", "page": 20, "area": "numbers", "unit": "Brojevi"},
            {"id": "g2-2026-002", "text": "poredi i uređuje brojeve do 100", "page": 20, "area": "numbers", "unit": "Brojevi"},
            {"id": "g2-2026-003", "text": "oduzima brojeve do 100", "page": 20, "area": "numbers", "unit": "Brojevi"},
            {"id": "g2-2026-004", "text": "rešava tekstualne zadatke sa jednom i dve računske operacije", "page": 21, "area": "numbers", "unit": "Brojevi"},
            {"id": "g2-2026-005", "text": "koristi znakove $<$ i $>$ za poređenje brojeva", "page": 20, "area": "numbers", "unit": "Brojevi"},
            {"id": "g2-2026-006", "text": "procenjuje rezultat sabiranja i oduzimanja do 100", "page": 21, "area": "numbers", "unit": "Brojevi"},
        ],
    },
}

REGISTRY = [record["id"] for grade in GRADES for record in TOPICS[grade]]

ALIASES = {"mat-brojevi": ["mat-brojevi-do-10"]}

UNMAPPED: dict[str, str] = {}

SOURCES = {
    "rule": "paraphrase",
    "evidence": "Fixture corpus for tests; texts are written for this repository.",
    "acts": [],
}

DIGRAPHS = {
    "manji": "digraph",
    "najmanjeg": "digraph",
    "njihov": "digraph",
    "injekcija": "split:n|j",
    "odjek": "split:d|j",
}

# Notation rules used by the lint on the fixture: a pattern, the first grade
# that may use it and the outcome that introduces it.
NOTATION: list[dict] = []
