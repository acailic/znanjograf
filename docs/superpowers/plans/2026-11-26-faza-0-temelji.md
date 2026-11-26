# Phase 0 — Foundations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build everything that later content phases rely on — the `zg` toolchain with every gate of the spec, the diagnostic engine, and the site — proven on a small fixture corpus, so that grades can then be added one at a time without touching code.

**Architecture:** Hand-authored JSON under `data/` is the source of truth (Serbian Latin). `zg` (Python, stdlib only) loads it into an in-memory `Corpus`, runs gates that each return a list of `Issue`s, and builds `_site/` in both scripts. The site is plain HTML/CSS/ES modules; the engine is pure JS tested with `node --test`. Work is split into tasks with strict file ownership so that up to ten agents can build in parallel in one working tree.

**Tech stack:** Python ≥ 3.12 standard library; Node ≥ 22 built-in test runner; KaTeX 0.19.1 vendored; no bundler, no framework, no CDN.

**Spec:** `docs/superpowers/specs/2026-11-26-znanjograf-design.md` (the source of truth; read §5–§12 first).

## Global Constraints

- Python standard library only in `zg/`. No `eval`, no pip dependencies.
- English identifiers, Serbian content: file names, JSON keys, commands and code are English; every string a pupil or teacher reads is Serbian Latin. Tool messages (`Issue.message`) are Serbian Latin; rule codes are English.
- Latin is the source of truth. Never hand-write Cyrillic; it is generated.
- Never copy text, data or code from `cn-math-taxonomy` or any other curriculum dataset.
- Ids are forever: `^mat-[a-z0-9]+(-[a-z0-9]+)*$`, ≤ 48 chars; question id `<topic-id>-q<n>`.
- Math in `$…$` LaTeX; decimal comma inside math is `{,}`; `\cdot`, `:`, `15\,\%`; `\text{…}` only for units.
- Serbian decimal comma, space as thousands separator, `15 %`, Latin unit symbols in both scripts.
- Each topic: ≥ 2 `basic` and ≥ 2 `standard` questions.
- One file, one owner. Agents never run `git`; the coordinator commits each task's files after review.
- Every task ends green on: `python3 -m unittest discover -s tests -q` and `node --test tests/node/`.

---

## CONTRACTS (read before any task in Part B)

### C1. Package layout

```
zg/
  __init__.py  __main__.py  paths.py  jsonio.py  corpus.py  issues.py
  checks/__init__.py  checks/schema.py  checks/graph.py  checks/coverage.py
  checks/bank.py  checks/figure.py
  dsl.py  mathcheck.py
  translit/__init__.py  translit/protect.py  translit/rules.py
  lint/__init__.py  lint/notation.py  lint/text.py
  blind.py  ledger.py  build.py  report.py  review.py
site/
  index.html  mapa/index.html  dijagnostika/index.html  o-projektu/index.html
  css/zg.css  js/…  vendor/katex/…
tests/
  __init__.py  helpers.py  fixtures/…  test_*.py  node/*.test.js
```

### C2. `zg.issues`

```python
@dataclass(frozen=True)
class Issue:
    path: str      # repo-relative file path, e.g. "data/math/g1/topics.json"
    where: str     # locator, e.g. "mat-sabiranje-do-20" or "topics[2].curriculum[0]"
    code: str      # rule id from the table in C8
    message: str   # Serbian Latin, says what and why

class Issues(list):
    def add(self, path: str, where: str, code: str, message: str) -> None
    def codes(self) -> set[str]
    def report(self, stream=None) -> int        # prints sorted "path: where: code: message" lines + summary; returns len(self)
```

### C3. `zg.corpus`

```python
class CorpusError(Exception): ...

@dataclass
class Edition:
    id: str                 # "g1-2026"
    grade: int
    raw: dict               # the whole edition file
    outcomes: dict[str, dict]   # outcome id → record (first occurrence wins)

class Corpus:
    subject: str
    topic_list: list[dict]; question_list: list[dict]; edge_list: list[dict]   # file order
    topics: dict[str, dict]; questions: dict[str, dict]                         # first occurrence wins
    editions: dict[str, Edition]
    registry: set[str]; aliases: dict[str, list[str]]; unmapped: dict[str, str]; sources: dict
    topic_file: dict[str, str]; question_file: dict[str, str]; edition_file: dict[str, str]; edge_file: dict[int, str]
    load_errors: list[tuple[str, str]]         # (path, message) for files that failed to load or parse

    @classmethod
    def load(cls, subject: str = "math", root: Path | None = None) -> Corpus
    @classmethod
    def from_raw(cls, subject: str, raw: RawCorpus) -> Corpus
    # derived — raise CorpusError on unknown ids or cycles:
    prereqs(topic_id, strengths=("hard", "soft")) -> list[dict]
    hard_ancestors(topic_id) -> set[str]
    ancestors(topic_id) -> set[str]            # any strength
    descendants(topic_id) -> set[str]
    learning_order() -> list[str]              # grade asc, then file order within grade
    grade_exits(grade) -> list[str]            # learning order
    bank(topic_id) -> list[dict]               # file order

@dataclass
class RawCorpus:                # what the fixture helpers build
    grades: list[int]
    topics: dict[int, list[dict]]        # grade → records in file order
    edges: dict[int, list[dict]]         # grade → records (the file of the dependent topic's grade)
    questions: dict[int, list[dict]]
    editions: dict[str, dict]            # edition id → edition file
    registry: list[str]; aliases: dict[str, list[str]]; unmapped: dict[str, str]; sources: dict
    def copy(self) -> RawCorpus
```

### C4. On-disk data shapes

- `data/<subject>/meta.json`: `{"subject": "math", "name": "Matematika", "grades": [1, …, 8], "areas": ["numbers", "geometry", "data"]}`
- `data/<subject>/g<N>/topics.json` — array, file order = curriculum order. `edges.json`, `questions.json` — arrays.
- `data/curriculum/<subject>/<edition>.json` — see spec §5.3. Outcome ids match `^g[1-8]-\d{4}-\d{3}$`; edition ids `^g[1-8]-\d{4}$`.
- `data/curriculum/sources.json`: `{"rule": "verbatim" | "paraphrase", "evidence": "…", "acts": [{"title": "…", "gazette": ["10/2017", …], "url": "…", "retrieved": "YYYY-MM-DD"}]}`
- `data/registry.json`: `{"topics": ["mat-…", …]}`. `data/aliases.json`: `{"old-id": ["mat-…"]}`. `data/curriculum/unmapped.json`: `{"<outcome id>": "reason"}`.
- `data/review/teachers.json`: `{"mat-…": {"name": "…", "role": "…", "date": "YYYY-MM-DD", "note": "…"}}` (optional file).

### C5. Field reference for validators

Topic: `id, grade, area, unit, kind, name, summary, mastery (2–3), curriculum[{edition, outcome, match}], root_reason?`
Edge: `topic, requires, strength, reason`
Question: `id, topic, level, type, prompt, figure?, choices?[{id, text}], answer, check, round_to?, explanation, points_to?`
Outcome file: `edition, grade, applies_from, themes?[{name, area?, hours?, content?, page?}], outcomes[{id, text, page, code?, level?, area?, unit?}], notes?`
Figure: `kind, alt, … params by kind`.

Enums: `area ∈ numbers|geometry|data`; `kind ∈ concept|procedure|problem|reasoning`; `level ∈ basic|standard`; `type ∈ numeric|choice`; `strength ∈ hard|soft`; `match ∈ exact|partial`; outcome `level ∈ basic|medium|advanced`.

### C6. Answer check DSL

S-expression parsed by `zg.dsl.parse(text) -> tuple | Fraction | str` with nesting depth ≤ 12 and ≤ 200 nodes. Atoms: integer `-3`, exact decimal `2.5`, `pi`. Operators (n-ary unless noted): `+ - * /`, `pow` (2), `sqrt` (1), `abs`, `min`, `max`, `floor`, `ceil`, `round` (1–2), `mean`, `median`, `mode`, `gcd`, `lcm`, `mod` (2), `percent` (2). `/` is `a / (b * c * …)`; a zero divisor is a parse-time value error reported as `S-check`.

```python
# zg/mathcheck.py
def evaluate(node) -> Fraction | Decimal       # exact; sqrt of a non-square gives Decimal with 50 digits
def parse_answer(text: str) -> Fraction | Decimal | None   # "15", "3,5", "3/4", "2 3/4", "-7", "1 000", "3.14"
def format_value(value, round_to: int | None = None) -> str  # canonical answer text
def answers_equal(expected, given, round_to: int | None = None) -> bool
def rational(value, round_to: int | None = None) -> tuple[str, str]   # ("numerator", "denominator") as decimal strings, for the JS bundle
```

### C7. Engine (JS, `site/js/engine/`)

All pure; no DOM, no storage, no fetch.

```js
// graph.js
export function buildIndex(topics, edges, aliases)
// topics: [{id, grade, area, unit, kind, name}] in file order; edges: [[topic, requires, "hard"|"soft"]]
// aliases: {oldId: [id, …]}
// → { topicIds, gradeOf: Map, prereqsOf(id) -> [{id, strength}], hardAncestorsOf(id) -> Set,
//     ancestorsOf(id) -> Set, learningOrder(ids) -> string[], gradeExits(grade) -> string[],
//     resolveAlias(id) -> string[] }

// rational.js
export function rat(num: bigint, den: bigint)            // {n: bigint, d: bigint}, normalised, d > 0
export function parseRat(text)                           // {n, d} | null ; mirrors mathcheck.parse_answer

// answer.js
export function isStrongAnswer(question, correct)        // numeric && correct && !(integer in −10..10)
export function isCorrect(question, response)            // response {type:"numeric", value} | {type:"choice", choiceId}
                                                        // question carries answerRational [num, den] strings

// verdict.js
export const STATUS = Object.freeze({ UNTESTED:"untested", MASTERED:"mastered", SHAKY:"shaky", WEAK:"weak", INFERRED:"inferred" })
export function verdictOf(evidence)                      // evidence: [{question, correct}] in asked order
                                                        // → {status, done}

// session.js
export function createSession({ scope, index, bank, budget = 25, history = {} })
// scope: {kind:"topic", id} | {kind:"unit", grade, unit} | {kind:"grade", grade} | {kind:"grade-full", grade}
// bank: {topicId: [question, …]}; history: {questionId: counter}
export function next(state)     // {kind:"question", topicId, question, role} | {kind:"paused", asked} | {kind:"done"}
export function apply(state, { questionId, correct })    // throws Error("ZG_OUT_OF_SYNC") if questionId ≠ next(state).question.id
export function extend(state)   // after "paused": new block of `budget`
export function reduce(log, ctx)                          // replay [{questionId, correct}]
export function summarise(state)                         // see below

// result.js
// summarise(state) → { roots:[{id, confirmed, missed:[qid]}], path:[{id, status}], shaky:[id],
//                      counts:{mastered, shaky, weak, inferred, untested}, untested:[id],
//                      outcomes:[{edition, id}] }

// encode.js
export function encodeSession({ scope, log }) -> string   // "v1." + base64url(JSON) ; decodeSession(text) -> {scope, log} | null
```

**Algorithm (normative).** `topicsInScope`: `topic` → `[id]`; `unit` → topics of `grade` with that `unit`; `grade` → `gradeExits(grade)`; `grade-full` → all topics of the grade. Iterate the scope in reverse learning order; skip topics with a status. `judge(t)`: ask first unused `standard`; wrong → ask first unused `basic` → wrong = `weak`, right = `shaky`; right and strong → `mastered`; right and not strong → ask second unused `standard` → right = `mastered`, wrong = `shaky`. Question choice = unused of the level, lowest history counter first, then file order. After `mastered`: every status-less hard ancestor becomes `inferred`. After `weak`: push `t` to the frontier. Drain the frontier FIFO: for each weak `w`, judge each status-less **hard** prerequisite nearest-first (reverse learning order); each new `weak` is pushed. If after that no hard prerequisite of `w` is `weak`, judge its status-less **soft** prerequisites the same way. A topic with no question left of the needed level is `weak`. Every asked question counts toward the block budget; on reaching the budget `next()` returns `paused`. Root = `weak` with no `weak` hard ancestor; `confirmed` iff every hard ancestor of the root has a status other than `untested`. `path` = all `weak` topics lying on a hard-edge path from a root to a scope topic, plus `shaky` topics on those paths, in learning order. `missed` = ids of questions answered wrong while judging the root.

### C8. Rule codes (exact strings)

| Gate | Codes |
|---|---|
| validate | `V1-json`, `V1-duplicate-key`, `V2-unknown-field`, `V2-missing-field`, `V2-type`, `V3-id-format`, `V3-id-duplicate`, `V3-id-unregistered`, `V3-id-unknown`, `V3-qid-format`, `V4-enum`, `V4-grade`, `V5-edge-endpoint`, `V5-self-loop`, `V5-duplicate`, `V5-reverse-pair`, `V5-grade-order`, `V5-redundant`, `V5-wrong-file`, `V6-cycle`, `V6-root-reason-missing`, `V6-root-reason-unneeded`, `V6-isolated`, `V7-outcome-missing`, `V7-outcome-unmapped`, `V7-unmapped-stale`, `V7-topic-without-outcome`, `V7-edition-grade`, `V8-bank-count`, `V8-choice-count`, `V8-choice-ids`, `V8-choice-text`, `V8-points-to`, `V8-numeric-answer`, `V8-round-to`, `V9-figure-kind`, `V9-figure-alt`, `V9-figure-param`, `V9-figure-geometry`, `V10-dollar`, `V11-alias-chain`, `V11-alias-target` |
| verify | `S-check-parse`, `S-check-depth`, `S-check-zero`, `S-answer-mismatch`, `S-choice-value`, `S-round-to` |
| lint | `L1-notation`, `L2-folded`, `L3-digraph`, `L4-orthography`, `L5-length`, `L6-near-duplicate`, `L7-mixed-script` |

Gate function signatures (each takes the corpus, mutates nothing, returns nothing, appends to `issues`):

```python
def run(corpus: Corpus, issues: Issues) -> None      # in zg.checks.schema, .graph, .coverage, .bank, .figure, zg.lint.notation, zg.lint.text
def verify(corpus: Corpus, issues: Issues) -> None   # zg.mathcheck
```

### C9. Built site (`_site/`)

```
_site/index.html  mapa/index.html  dijagnostika/index.html  o-projektu/index.html  pregled/gN.html
_site/css/zg.css  _site/js/…  _site/vendor/katex/…
_site/podaci/index.lat.json  index.cir.json  gN.lat.json  gN.cir.json  ishodi/<edition>.lat.json  <edition>.cir.json
_site/cir/…                                  # full mirror; links inside stay inside the mirror
_site/manifest.json                          # {"data": "<sha256>", "script": "<sha256>", "built": "YYYY-MM-DDTHH:MM:SSZ"}
```

- `index.*.json`: `{subject, name, grades, areas, topics:[{id, grade, area, unit, kind, name}], edges:[[topic, requires, strength]], aliases, units:{grade:[names in order]}}`
- `gN.*.json`: `{topics:{id:{summary, mastery, curriculum, review}}, questions:{id:{…all fields…, answerRational:[num, den]}}}`
- Text fields are transliterated whole-tree; `$…$` spans, unit symbols, URLs and HTML tags are protected.
- `zg build --check` exits 1 if rebuilding would change any byte of `_site/`.

---

## Part A — Foundation (coordinator, sequential)

### Task 1: Package skeleton, `paths`, `jsonio`, `issues`, `corpus`

**Files:** Create `zg/__init__.py`, `zg/__main__.py`, `zg/paths.py`, `zg/jsonio.py`, `zg/issues.py`, `zg/corpus.py`, `zg/checks/__init__.py`, `zg/translit/__init__.py`, `zg/lint/__init__.py`, `tests/__init__.py`, `tests/helpers.py`.
**Produces:** everything in C2, C3.

- [ ] **Step 1: Write `tests/test_corpus.py`**

```python
import unittest
from zg.corpus import Corpus, CorpusError
from tests.helpers import fixture_raw

class CorpusTest(unittest.TestCase):
    def setUp(self):
        self.c = Corpus.from_raw("math", fixture_raw())

    def test_loads_all_grades_in_file_order(self):
        self.assertEqual(self.c.learning_order()[:2], ["mat-brojevi-do-10", "mat-sabiranje-do-10"])

    def test_ancestors_follow_strength(self):
        self.assertEqual(self.c.hard_ancestors("mat-sabiranje-do-100"),
                         {"mat-sabiranje-do-20", "mat-sabiranje-do-10", "mat-brojevi-do-10"})

    def test_soft_edge_is_not_a_hard_ancestor(self):
        self.assertIn("mat-sabiranje-do-10", self.c.ancestors("mat-poredjenje-do-100"))
        self.assertNotIn("mat-sabiranje-do-10", self.c.hard_ancestors("mat-poredjenje-do-100"))

    def test_excludes_are_not_required_by_same_grade(self):
        self.assertEqual(set(self.c.grade_exits(2)), {"mat-oduzimanje-do-100", "mat-zadaci-sa-sabiranjem"})

    def test_cycle_raises(self):
        raw = fixture_raw()
        raw.edges[1].append({"topic": "mat-brojevi-do-10", "requires": "mat-sabiranje-do-10", "strength": "hard", "reason": "x"})
        with self.assertRaises(CorpusError):
            Corpus.from_raw("math", raw).learning_order()
```

- [ ] **Step 2: Run `python3 -m unittest tests.test_corpus -v` → fails with `ModuleNotFoundError`.**
- [ ] **Step 3: Implement the modules to C2/C3.** `jsonio.load_json` raises `jsonio.DuplicateKeyError(path, key)` on a repeated object key; `sha256_obj(obj)` hashes `json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))`.
- [ ] **Step 4: Tests pass. Commit `feat(zg): package skeleton, corpus, issues`.**

### Task 2: Fixture corpus and test helpers

**Files:** Create `tests/fixtures/raw.py` (the only hand-written data in tests), `tests/helpers.py`.
**Produces:** `fixture_raw() -> RawCorpus` (fresh copy each call), `fixture_corpus() -> Corpus`, `find(raw, kind, id)`, `write_corpus(root, raw)` (writes a real tree for CLI tests).

Fixture = spec §5 shapes, 2 grades, 8 topics, 8 edges, 32 questions (2 basic + 2 standard each), editions `g1-2026` (5 outcomes) and `g2-2026` (6 outcomes), all outcomes mapped. It is **valid by definition**: every gate must return zero issues on it.

- [ ] **Step 1: Write the fixture and helpers.**
- [ ] **Step 2: Write `tests/test_fixture_is_wellformed.py`** asserting shapes only (counts, id patterns, 4 questions per topic).
- [ ] **Step 3: `python3 -m unittest discover -s tests -q` → OK. Commit `test: fixture corpus`.**

### Task 3: CLI, CI, KaTeX

**Files:** Modify `zg/__main__.py`; Create `.github/workflows/ci.yml`, `site/vendor/katex/` (from the npm tarball of `katex@0.19.1`: `dist/katex.min.js`, `dist/katex.min.css`, `dist/fonts/*.woff2`, `LICENSE`), `site/vendor/katex/VERSION`.

`__main__.py`: `argparse` with sub-commands `validate, verify, lint, build, serve, report, status, all`. Each command calls a function `cmd_<name>(args) -> int`; a command whose module does not exist yet prints `nije implementirano: <name>` and returns 2. `all` runs `validate`, `verify`, `lint`, `report --check`, `build --check` and returns 1 if any returns non-zero (2 counts as failure once Task 14 wires it; before that `all` returns 0 only if every implemented command passes).

CI (`.github/workflows/ci.yml`): on push/PR to `main`; Python 3.12 → `python3 -m zg all`; Node 22 → `node --test tests/node/`; upload `_site/` as artifact.

- [ ] **Step 1: Write `tests/test_cli.py`** (each unimplemented command exits 2; `validate` on the written fixture tree will be wired in Task 14).
- [ ] **Step 2:** Implement; vendor KaTeX; `node -e "require('./site/vendor/katex/katex.min.js')"` prints nothing and exits 0.
- [ ] **Step 3: Commit `feat(ci): CLI skeleton, workflow, vendored KaTeX`.**

---

## Part B — Parallel tasks (one agent each; no `git`; only the files listed)

Every task: write the failing tests first, run them, implement, run the whole suite, report the exact command output. Tests build mutated copies with `fixture_raw()` + `Corpus.from_raw` and assert on `issues.codes()`.

### Task 4 — `checks/schema.py` + `checks/graph.py`

**Files:** Create `zg/checks/schema.py`, `zg/checks/graph.py`, `tests/test_checks_schema.py`, `tests/test_checks_graph.py`.
**Consumes:** C2, C3, C5, C8, fixture. **Produces:** `schema.run(corpus, issues)`, `graph.run(corpus, issues)`.

`schema.run`: V1 (`jsonio` errors when present in `corpus.load_errors`), V2, V3, V4, V10 (`$` count even per string field), V11. Unknown field detection uses exact key sets per record type from C5.
`graph.run`: V5, V6. Must not use `Corpus` derived methods (they raise on broken graphs); implement its own DFS. `V5-redundant`: a `hard` edge `a→b` is redundant iff another path `a ⇝ b` exists using only `hard` edges without that edge; a `soft` edge is redundant iff any other path exists.

- [ ] Tests at minimum: unknown field → `V2-unknown-field`; missing `mastery` → `V2-missing-field`; id with uppercase → `V3-id-format`; topic absent from registry → `V3-id-unregistered`; edge to missing topic → `V5-edge-endpoint`; `a→b` and `b→a` → `V5-reverse-pair`; edge from grade 1 topic requiring grade 2 topic → `V5-grade-order`; adding `mat-sabiranje-do-100 →hard mat-sabiranje-do-10` → `V5-redundant`; adding `mat-sabiranje-do-100 →soft mat-sabiranje-do-10` → `V5-redundant`; removing `root_reason` from `mat-brojevi-do-10` → `V6-root-reason-missing`; adding `root_reason` to `mat-sabiranje-do-10` → `V6-root-reason-unneeded`; cycle → `V6-cycle`; alias chain → `V11-alias-chain`; unbalanced `$` → `V10-dollar`. And: unmutated fixture → no codes starting with `V2`, `V3`, `V5`, `V6`, `V10`, `V11`.

### Task 5 — `checks/coverage.py` + `checks/bank.py`

**Files:** Create `zg/checks/coverage.py`, `zg/checks/bank.py`, `tests/test_checks_coverage.py`, `tests/test_checks_bank.py`.
**Produces:** `coverage.run(corpus, issues)`, `bank.run(corpus, issues)`.

`coverage.run`: V7 and outcome-file schema (ids `^g[1-8]-\d{4}-\d{3}$`, `page` positive int, `V7-edition-grade` when the edition's `grade` digit disagrees with its id). `bank.run`: V8 and question-record schema (reuse helpers from `checks/schema.py`).
`V8-points-to`: every target must be a hard ancestor of the question's topic (use `Corpus.hard_ancestors`; skip with no issue when the graph raises `CorpusError`).
`V8-numeric-answer`: `mathcheck.parse_answer(answer)` must succeed; call it lazily (import inside the function) so this task does not depend on Task 6 being merged; if the import fails, emit nothing.

- [ ] Tests at minimum: topic citing a missing outcome → `V7-outcome-missing`; delete an outcome's only mapping and do not list it → `V7-outcome-unmapped`; list it in `unmapped` → clean; keep it in `unmapped` after restoring its mapping → `V7-unmapped-stale`; topic with empty `curriculum` → `V7-topic-without-outcome`; edition id `g2-2026` with `"grade": 3` → `V7-edition-grade`; three questions on a topic → `V8-bank-count`; choice with 2 options → `V8-choice-count`; `answer` not among choice ids → `V8-choice-ids`; duplicate choice text → `V8-choice-text`; `points_to` to a non-ancestor → `V8-points-to`; `sqrt` question without `round_to` is Task 6's concern (not here).

### Task 6 — `dsl.py`, `mathcheck.py`

**Files:** Create `zg/dsl.py`, `zg/mathcheck.py`, `tests/fixtures/answer-vectors.json`, `tests/test_dsl.py`, `tests/test_mathcheck.py`.
**Produces:** C6, plus `verify(corpus, issues)` in `mathcheck.py`.

`verify`: `S-check-parse` (`DslError`), `S-check-depth`, `S-check-zero`; `S-answer-mismatch` when `not answers_equal(evaluate(parse(check)), parse_answer(answer), round_to)`; `S-choice-value` when a numeric option is wrong yet equals the answer, or the correct option's text does not evaluate to the answer; when no option parses as a number, the correct option's `text` must equal `check` exactly (the fixture's `mat-geometrijski-oblici` questions work this way); `S-round-to` when the value is irrational (`Decimal`) and `round_to` is missing. Choice texts are parsed with `parse_answer` first, then `dsl.parse`.

`tests/fixtures/answer-vectors.json` is shared with the JS engine (Task 11): `[{"text": "3,5", "num": "7", "den": "2"}, {"text": "2 3/4", "num": "11", "den": "4"}, …]` — at least 24 vectors including negatives, leading `+`, spaces as thousands separators, `1.000` (= 1000), `1.5` (= 1.5), `007`, `-0`, and invalid inputs (`""`, `"3,,5"`, `"1/0"`, `"abc"`, `"3 4"`).

- [ ] Tests at minimum: `(+ 8 7)` → 15; `(/ 3 4 5)` → 3/20 exactly; `(percent 15 200)` → 30; `(sqrt 2)` is `Decimal`; `(/ 1 0)` → `S-check-zero`; 13-deep nesting → `S-check-depth`; `(foo 1)` → `S-check-parse`; changing a fixture answer to `"16"` → `S-answer-mismatch`; wrong choice rewritten to the correct value → `S-choice-value`; every vector in `answer-vectors.json` parses to `Fraction(num, den)`.

### Task 7 — `translit/` + `lint/text.py`

**Files:** Create `zg/translit/protect.py`, `zg/translit/rules.py`, `zg/lint/text.py`, `tests/fixtures/translit-golden.json`, `tests/test_translit.py`, `tests/test_lint_text.py`, `tools/add-digraphs.py` (repo root `tools/`, stdlib script; optional helper).

**Produces:**

```python
# translit/protect.py
def split_protected(text: str) -> list[tuple[str, bool]]   # (segment, is_protected): `$…$`, URLs, HTML tags, unit tokens
UNIT_PATTERN: re.Pattern                                  # mm|cm|dm|km|m|kg|g|mg|t|l|ml|dl|h|min|s|°C|km/h|m/s|m²|m³|a|ha|din
# translit/rules.py
def to_cyrillic(text: str) -> str
def to_latin(text: str) -> str
def translit_obj(obj, fn=to_cyrillic)                     # deep over dict/list/str; keys untouched
def fold(text: str) -> str                                # → lowercase ASCII Latin without diacritics
def collation_key(text: str) -> tuple                      # Serbian alphabet order: а б в г д ђ е ж з и ј к л љ м н њ о п р с т ћ у ф х ц ч џ ш
def needs_lexicon(word: str) -> bool                      # contains lj, nj or dž
# lint/text.py
def run(corpus, issues) -> None                           # L2–L5, L7 on built text
def check_mixed_script(text, where, path, issues) -> None  # L7
```

Digraph rule: `lj`, `nj`, `dž` are digraphs inside a word unless `lint/digraphs.json` lists the word; the lexicon maps the lowercase word to `"digraph"` or `"split"` (`injekcija` → `split:n|j`, `odjek` → `split:d|j`). For this task the lexicon file is `data/lint/digraphs.json` (create it with every fixture word classified); `tools/add-digraphs.py` prints words from the corpus missing from the lexicon.

- [ ] Tests at minimum: `Mila ima 8 kuvanica` → `Мила има 8 куваница`; round trip on 60+ real sentences; `$3{,}5$ cm` untouched; `<b>duplo</b> veće` → `<b>дупло</b> веће`; `injekcija` → `инјекција` with the lexicon entry and validation-relevant `needs_lexicon` true; `множење` → `množenje`; `fold("Množenje") == "mnozenje"`; `collation_key` orders `lj < m` and `nj < o`; `mnozenje` beside existing `množenje` → `L2-folded`; `3.5` in prose → `L4-orthography`; `15%` → `L4-orthography`; `dž` word absent from the lexicon → `L3-digraph`; 201-char prompt on a grade-1 topic → `L5-length`; Cyrillic text containing a bare Latin word → `L7-mixed-script`.
- [ ] `tests/fixtures/translit-golden.json`: `[[latin, cyrillic], …]`, ≥ 40 pairs now (the 300 target is reached from real content in later phases).

### Task 8 — `lint/notation.py` + `checks/figure.py`

**Files:** Create `zg/lint/notation.py`, `zg/checks/figure.py`, `tests/test_lint_notation.py`, `tests/test_checks_figure.py`, `tests/fixtures/figures.json`.
**Produces:** `notation.run(corpus, issues)` (L1), `figure.run(corpus, issues)` (V9), `figure.KINDS`, `figure.validate(spec) -> list[str]`.

Notation rules live in `data/lint/notation.json`: `[{"pattern": "\\\\times|\\\\cdot", "min_grade": 2, "outcome": "g2-2026-003", "note": "množenje"}, …]`. A rule applies to `$…$` spans of a topic's questions; a hit below `min_grade` is `L1-notation`. A rule whose `outcome` is not in the corpus is skipped and reported once as `L1-rule-outcome` (warning). Create the file with rules for `\times`, `\cdot`, `:` (division), `\frac`, `{,}` (decimals), `sqrt`, `^`, `pi`, letters used as variables, `<`, `>`, and cite fixture outcomes.

Figures: kinds `numberline, fractionbar, pie, dots, bars, pictogram, grid, polygon, angle, axes, clock, table`. `figure.run` checks kind, `alt` ≥ 20 chars, and geometry: for `polygon`, each `side` label length must match its coordinates within 1 %.

- [ ] Tests at minimum: `\times` in a grade-1 question → `L1-notation`; the same in grade 2 → clean; rule citing a missing outcome → `L1-rule-outcome` and nothing else; `alt` of 5 chars → `V9-figure-alt`; kind `"cube"` → `V9-figure-kind`; polygon labelled side 5 with coordinates 4 units apart → `V9-figure-geometry`; every figure in `tests/fixtures/figures.json` (one per kind) passes `figure.validate`.

### Task 9 — `ledger.py`, `blind.py`, `report.py`

**Files:** Create `zg/ledger.py`, `zg/blind.py`, `zg/report.py`, `tests/test_ledger.py`, `tests/test_blind.py`, `tests/test_report.py`.
**Produces:**

```python
# ledger.py — data/ledger.json: {"<gate>": {"<record id>": "<sha256 of canonical record>"}}
LEDGER = ROOT / "data" / "ledger.json"
GATES = ("verify", "blind-solve", "classify", "cueing", "edges")
def content_hash(record: dict) -> str
def load_ledger() -> dict            # {} if missing
def mark(gate: str, ids: list[str], records: dict[str, dict]) -> None   # writes the file
def stale(gate: str, corpus: Corpus) -> list[str]   # ids whose hash differs or is missing
# blind.py
def make_sheet(corpus, grade: int, script: str = "cyr") -> dict   # {"items":[{"id", "prompt", "figure", "choices":[{id,text}]}]} in random order (seedable)
def diff(corpus, grade: int, answers: dict) -> list[dict]        # answers: {"<qid>": {"answer","check","unique","assumptions","distractors":{id:0-3}}}
                                                                   # → failures [{"id","reasons":[…]}]
# report.py
def stats(corpus) -> dict            # {"topics", "edges", "hard", "soft", "questions", "outcomes", "by_grade":{…}}
def status(corpus) -> dict           # per grade: counts + per-gate verified/stale
def readme_block(corpus) -> str      # the markdown table between <!-- zg:stats --> markers
def check_readme(text: str, block: str) -> bool
```

- [ ] Tests at minimum: hash is stable across key order; `stale` reports a changed record and an unmarked one; `diff` passes a clean answer set and fails on wrong answer, own-check mismatch, `unique: false`, non-empty `assumptions`, distractor rated 2; `stats` on the fixture = 8 topics / 8 edges (6 hard, 2 soft) / 32 questions / 11 outcomes; `readme_block` round-trips through `check_readme`.

### Task 10 — `build.py`

**Files:** Create `zg/build.py`, `tests/test_build.py`.
**Consumes:** `translit.rules` (Task 7 contract), `mathcheck.rational` (Task 6 contract), `corpus`. **Produces:**

```python
def build_site(root: Path | None = None, out: Path | None = None) -> dict   # returns the manifest
def check_site(root: Path | None = None, out: Path | None = None) -> list[str]   # differences
def serve(root: Path | None = None, port: int = 8765) -> None                  # http.server, rebuilds on each request
```

Copy `site/` → `_site/` and `site/` → `_site/cir/` with every text asset (`.html`, `.css`, `.js`) and data transliterated (in `cir/`, `js/strings.js` is replaced by its transliterated object). Write `podaci/*.json` per C9 from the corpus.
If `translit` is not importable yet, tests may import a local stub — but the committed code must import `zg.translit.rules`.

- [ ] Tests at minimum: build on the fixture tree creates every C9 file; `index.cir.json` names are Cyrillic and `$…$` spans are byte-identical to the Latin file; `answerRational` of a `3/4` answer is `["3", "4"]`; second build changes nothing and `check_site` returns `[]`; editing a topic name makes `check_site` non-empty; links inside `_site/cir/mapa/index.html` point inside `cir/`.

### Task 11 — Engine (`site/js/engine/`)

**Files:** Create `graph.js`, `rational.js`, `answer.js`, `verdict.js`, `session.js`, `result.js`, `encode.js`, `tests/node/engine.test.js`, `tests/node/helpers.js` (reads `tests/fixtures/answer-vectors.json` and the fixture built by `tests/helpers.py` via a JSON dump in `tests/fixtures/engine-fixture.json` — the coordinator generates it in Task 14; until then load it through `child_process` `python3 -c …`; keep that in a helper so it is one line to change).
**Produces:** C7 exactly.

- [ ] Tests at minimum (node:test + assert): all vectors in `answer-vectors.json` parse to the expected rational; simulated pupil who knows all ancestors-closed sets: for **every** topic `k` used as the single missing root, diagnosing `mat-zadaci-sa-sabiranjem` returns `k` among `roots` with `confirmed === true`; knows-everything pupil reaches `mastered` on all scope topics with ≤ 2 questions per topic; knows-nothing pupil: every root is `confirmed`, and no topic is `mastered`; a pupil who guesses every answer: over 2000 seeded random sessions on the choice-only fixture topic `mat-geometrijski-oblici` (four options, so pure chance is 1/16) the `mastered` rate is below 10 %; budget: `next()` returns `paused` after exactly `budget` questions and `extend()` continues; replay: `reduce(log)` equals the live state for any prefix; `apply` with a wrong question id throws `ZG_OUT_OF_SYNC`; `encodeSession`/`decodeSession` round-trip and reject garbage; `gradeExits(2)` equals the Python fixture expectation.

### Task 12 — Figures, layout, graph view, KaTeX wrapper

**Files:** Create `site/js/figure.js`, `site/js/layout.js`, `site/js/graph-view.js`, `site/js/katex.js`, `tests/node/figure.test.js`, `tests/node/layout.test.js`, `tests/node/katex.test.js`.
**Produces:**

```js
export const FIGURE_KINDS = [...12]
export function renderFigure(spec) -> {svg: string, alt: string, width: number, height: number}
export function layout({nodes, edges, focus}) -> {width, height, nodes:[{id, x, y, w, h, band}], edges:[{from, to, strength, points:[[x,y],…]}]}
export function toSvg(layoutResult, verdicts) -> string          // verdicts: {id: "mastered"|…}
export function mount(container, layoutResult, verdicts, onSelect) -> void
export function texToHtml(tex) -> string                          // KaTeX htmlAndMathml
export function renderInto(el, tex) -> void                       // falls back to <code> on error
```

Layout per spec §12.3: x = longest-path layer (+1 per edge), y = grade band with as many rows as its widest cell needs, cap 8 rows with overflow as `+N`; no two nodes overlap; every edge goes left→right.

- [ ] Tests at minimum: each kind renders valid SVG with a `<title>` equal to `alt`; `numberline` with min 0 max 10 has 11 ticks; a 40-node layered graph has zero overlapping rectangles and zero edges pointing left; bands never interleave; `toSvg` marks hard edges `stroke-dasharray`-free and soft edges dashed; `texToHtml("3{,}5+\\frac{1}{2}")` contains `class="katex"`; `texToHtml("\\text{abc}")` returns the fallback markup.

### Task 13 — Site pages and UI

**Files:** Create `site/index.html`, `site/mapa/index.html`, `site/dijagnostika/index.html`, `site/o-projektu/index.html`, `site/css/zg.css`, `site/js/strings.js`, `site/js/data.js`, `site/js/storage.js`, `site/js/common.js`, `site/js/ui/question.js`, `site/js/ui/progress.js`, `site/js/ui/result.js`, `site/js/pages/home.js`, `site/js/pages/map.js`, `site/js/pages/diagnose.js`, `site/js/pages/about.js`, `tests/node/strings.test.js`, `tests/node/storage.test.js`.
**Consumes:** C7, C9, Task 12 exports. **Produces:** `data.js` (`loadIndex(script)`, `loadGrade(n, script)`, `loadOutcomes(edition, script)`, `currentScript()`), `storage.js` (`loadSession`, `saveSession`, `clearAll`, `getPrefs`, `setPrefs`, `pushHistory`, wrapped `try/catch`), `common.js` (`initCommon`, `setScript`, `parseHash`, `formatHash`).

All UI strings live in `strings.js` as one exported object of Serbian Latin; nothing else contains user-facing text. All parameters live in the `#` fragment (`mat-…`, `razred=5`, `rezultat=…`, `pismo=cir|lat`). Touch targets ≥ 44 px; `lang="sr-Latn"` / `sr-Cyrl"` set on `<html>`; every page works with JS-driven content and has a `<noscript>` sentence.

- [ ] Tests at minimum (node, no DOM for logic): `parseHash("#mat-sabiranje-do-20&pismo=cir")` → `{topic:"mat-sabiranje-do-20", script:"cyr"}`; `formatHash` round-trips; every value in `strings.js` contains only Serbian Latin or protected spans and no Cyrillic; `storage` functions swallow a throwing `localStorage` and still return defaults.

---

## Part C — Integration (coordinator)

### Task 14: Wire, generate the engine fixture, release

**Files:** Modify `zg/__main__.py` (wire `validate` → `schema.run, graph.run, coverage.run, bank.run, figure.run`; `verify` → `mathcheck.verify`; `lint` → `notation.run, text.run`; `all`), `tests/helpers.py` (`dump_engine_fixture()` writing `tests/fixtures/engine-fixture.json`), `tests/test_cli.py`, `.github/workflows/ci.yml` (Pages deploy on `main`).

- [ ] **Step 1:** `python3 -m zg validate` on the fixture tree → `OK`.
- [ ] **Step 2:** `python3 -m unittest discover -s tests -q` → OK; `node --test tests/node/` → all pass.
- [ ] **Step 3:** `python3 -m zg build` and `python3 -m zg build --check` → no differences; open `_site/` in a browser, run a scripted session on both scripts.
- [ ] **Step 4:** Commit `feat: wire all gates and build`; push; create the public repo `acailic/znanjograf`; confirm Pages serves `_site/` and CI is green.

## Self-review notes

- Spec coverage in this plan: §5–§9 (data, conventions, tool, verification, gates), §10–§11 (engine, tests, CI), §12 (site). Phases 1–8 of spec §14 get their own plans; this plan is Phase 0.
- Deliberately out of this plan: `review.py` (Task 15 of the content phase, when there is content to review), real curriculum data, the notation table beyond fixture rules, the 300-pair golden corpus (grows with content).
