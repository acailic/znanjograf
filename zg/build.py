"""Builds ``_site/``: the static site twice — Latin at the root, Cyrillic under ``cir/`` — plus data bundles.

Only the text a pupil or teacher reads is transliterated. Ids, enum values and option ids stay
as they are, so the engine behaves identically in both trees.
"""

from __future__ import annotations

import hashlib
import html
import re
import shutil
import tempfile
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from zg import corpus as corpus_module
from zg import jsonio, paths
from zg.mathcheck import parse_answer, rational
from zg.translit import rules as translit

LAT, CYR = "lat", "cyr"
DATA_DIR = "podaci"
MIRROR = "cir"
AREAS = ("numbers", "geometry", "data")
# Keys whose string values are machine values, never text to transliterate.
KEEP_KEYS = frozenset({"id", "outcome", "area", "level", "kind", "symbol", "edition", "match", "hours", "page", "applies_from", "strength"})
MANIFEST = "manifest.json"

_JS_STRING = re.compile(r"""("(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*'|`(?:[^`\\]|\\.)*`)(\s*:)?""", re.S)
_JS_INTERP = re.compile(r"(\$\{[^}]*\})")  # the capturing group keeps each ${…} in the split
# The static text of a page: its title, its <noscript> sentence and the fallback inside <main>
# that the page script replaces (it must be readable before, or without, the script).
_HTML_TEXT = re.compile(r"(<(?:title|noscript|main)\b[^>]*>)(.*?)(</(?:title|noscript|main)>)", re.S | re.I)
# A page carries this mark where the notice about unfinished content belongs (right after the
# header). The build replaces it with the notice, or with nothing once every grade has questions.
DRAFT_MARK = "<!--zg:draft-->"
# The notice as the build writes it: a note, read once, in reading order (it is no landmark).
DRAFT_BLOCK = '<div class="zg-wrap zg-draft" role="note"><p class="zg-note zg-note-warn">{notice}</p></div>\n'


# ----- public ----------------------------------------------------------------------

def build_site(root: Path | str | None = None, out: Path | str | None = None, site_src: Path | str | None = None) -> dict:
    """Write the whole site for both scripts. Returns the manifest."""
    root = Path(root) if root is not None else paths.ROOT
    out = Path(out) if out is not None else root / "_site"
    source = Path(site_src) if site_src is not None else paths.SITE_SRC
    corpus = corpus_module.Corpus.load("math", root=root)
    if out.exists():
        shutil.rmtree(out)
    notice = draft_notice(corpus)
    notices = {LAT: notice, CYR: None if notice is None else translit.to_cyrillic(notice, corpus.lexicon)}
    for target, script in ((out, LAT), (out / MIRROR, CYR)):
        _copy_site(source, target)
        if script == CYR:
            _adapt_tree(target, corpus.lexicon)
        _fill_draft(target, notices[script])
        _write_bundles(target / DATA_DIR, corpus, script)
    manifest = {"data": jsonio.sha256_obj(_index(corpus, _keep)), "script": _script_hash(source), "built": _now()}
    jsonio.dump(manifest, out / MANIFEST)
    return manifest


def check_site(root: Path | str | None = None, out: Path | str | None = None, site_src: Path | str | None = None) -> list[str]:
    """Rebuild into a temporary directory and list every file that would differ from ``out``."""
    root = Path(root) if root is not None else paths.ROOT
    out = Path(out) if out is not None else root / "_site"
    if not out.exists():
        return [f"{out.name}/ ne postoji; pokreni: python3 -m zg build"]
    with tempfile.TemporaryDirectory() as tmp:
        fresh = Path(tmp) / "site"
        build_site(root, fresh, site_src)
        return _diff_trees(fresh, out)


def serve(root: Path | str | None = None, port: int = 8765) -> None:
    """Local server that rebuilds whenever a source file is newer than the built site."""
    root = Path(root) if root is not None else paths.ROOT
    out = root / "_site"

    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 — the name is the http.server API
            if _stale(root, out):
                build_site(root, out)
            super().do_GET()

    def factory(*args, **kwargs) -> Handler:
        return Handler(*args, directory=str(out), **kwargs)

    if not out.exists():
        build_site(root, out)
    with ThreadingHTTPServer(("127.0.0.1", port), factory) as httpd:
        print(f"Znanjograf: http://127.0.0.1:{port}/  (Ctrl+C za kraj)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


# ----- site tree --------------------------------------------------------------------

def _copy_site(source: Path, target: Path) -> None:
    if not source.exists():
        target.mkdir(parents=True)
        return
    shutil.copytree(source, target, ignore=shutil.ignore_patterns(DATA_DIR))


def draft_notice(corpus: corpus_module.Corpus) -> str | None:
    """What a reader must know before relying on the site while the content is still being written.

    Says which grades have their program and which have topics with questions, so that nobody is
    sent to a diagnosis that has nothing to ask. ``None`` once every grade has questions, whatever
    the programs: the notice must not outlast the state it describes.
    """
    every = sorted(corpus.grades)
    asked = sorted({
        corpus.topics[record["topic"]]["grade"]
        for record in corpus.questions.values()
        if record.get("topic") in corpus.topics
    })
    if not every or asked == every:
        return None
    with_program = sorted({edition.grade for edition in corpus.editions.values()})
    if with_program:
        program = f"Nastavni program je upisan {_grades_text(with_program, every)}"
    else:
        program = "Nastavni program nije još upisan ni za jedan razred"
    if asked:
        waiting = [grade for grade in every if grade not in asked]
        content = f"teme i zadaci su upisani {_grades_text(asked, every)}, a {_grades_text(waiting, every)} su u pripremi"
    else:
        content = "teme i zadaci još nisu upisani ni za jedan razred, pa dijagnostika trenutno nema od čega da pita"
    return f"Sadržaj se još upisuje: ovo je rana javna verzija. {program}; {content}."


def _grades_text(grades: list[int], every: list[int]) -> str:
    """„za 1. razred“, „za 1. i 5. razred“, „za 2–4. razred“, „za sve razrede“ ili „ni za jedan razred“."""
    if not grades:
        return "ni za jedan razred"
    if grades == every:
        return "za sve razrede"
    parts: list[str] = []
    run: list[int] = []
    for grade in grades:
        if run and grade == run[-1] + 1:
            run.append(grade)
            continue
        parts += _run_parts(run)
        run = [grade]
    parts += _run_parts(run)
    if len(parts) == 1:
        return f"za {parts[0]} razred"
    return "za " + ", ".join(parts[:-1]) + " i " + parts[-1] + " razred"


def _run_parts(run: list[int]) -> list[str]:
    """Three or more grades in a row are a range; one or two are still named one by one."""
    if len(run) > 2:
        return [f"{run[0]}–{run[-1]}."]
    return [f"{grade}." for grade in run]


def _fill_draft(target: Path, notice: str | None) -> None:
    """Put ``notice`` where each page carries ``DRAFT_MARK``, and take the mark away when there is none.

    The mark itself is replaced wherever it stands, so one that is not on a line of its own is not
    left behind unnoticed.
    """
    block = "" if notice is None else DRAFT_BLOCK.format(notice=html.escape(notice))
    for file in target.rglob("*.html"):
        content = file.read_text(encoding="utf-8")
        if DRAFT_MARK in content:
            file.write_text(content.replace(DRAFT_MARK, block), encoding="utf-8")


def _adapt_tree(target: Path, lexicon: dict[str, str]) -> None:
    """Turn the copied Latin tree into the Cyrillic mirror."""
    for file in target.rglob("*.html"):
        text = file.read_text(encoding="utf-8")
        text = _HTML_TEXT.sub(lambda m: m.group(1) + translit.to_cyrillic(m.group(2), lexicon) + m.group(3), text)
        text = text.replace('data-pismo="lat"', 'data-pismo="cyr"').replace('lang="sr-Latn"', 'lang="sr-Cyrl"')
        file.write_text(text, encoding="utf-8")
    strings = target / "js" / "strings.js"
    if strings.exists():
        strings.write_text(_translit_js_strings(strings.read_text(encoding="utf-8"), lexicon), encoding="utf-8")


def _translit_js_strings(text: str, lexicon: dict[str, str]) -> str:
    """Transliterate the string literals of a JS file that are values, leaving keys and code alone."""

    def replace(match: re.Match) -> str:
        literal, colon = match.group(1), match.group(2)
        if colon:  # an object key written in quotes
            return match.group(0)
        quote, body = literal[0], literal[1:-1]
        pieces = _JS_INTERP.split(body)  # alternates: static text, ${…}, static text, …
        for index in range(0, len(pieces), 2):
            pieces[index] = translit.to_cyrillic(pieces[index], lexicon)
        return quote + "".join(pieces) + quote

    return _JS_STRING.sub(replace, text)


def _script_hash(source: Path) -> str:
    digest = hashlib.sha256()
    files = [p for p in source.rglob("*") if p.is_file()] if source.exists() else []
    for file in sorted(files):
        if DATA_DIR in file.relative_to(source).parts:
            continue
        digest.update(file.relative_to(source).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(file.read_bytes()).digest())
    return digest.hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stale(root: Path, out: Path) -> bool:
    manifest = out / MANIFEST
    if not manifest.exists():
        return True
    stamp = manifest.stat().st_mtime
    for folder in (paths.SITE_SRC, root / "data"):
        if folder.exists() and any(p.stat().st_mtime > stamp for p in folder.rglob("*") if p.is_file()):
            return True
    return False


def _diff_trees(fresh: Path, built: Path) -> list[str]:
    def files(base: Path) -> dict[str, Path]:
        return {p.relative_to(base).as_posix(): p for p in base.rglob("*") if p.is_file()}

    left, right = files(fresh), files(built)
    differences = []
    for name in sorted(set(left) | set(right)):
        if name not in left:
            differences.append(f"{name}: višak u izgrađenom sajtu")
        elif name not in right:
            differences.append(f"{name}: nedostaje u izgrađenom sajtu")
        elif name == MANIFEST:
            if _without_built(left[name]) != _without_built(right[name]):
                differences.append(f"{name}: drugačiji sadržaj")
        elif left[name].read_bytes() != right[name].read_bytes():
            differences.append(f"{name}: drugačiji sadržaj")
    return differences


def _without_built(path: Path) -> dict:
    data = jsonio.load(path)
    data.pop("built", None)
    return data


# ----- README in Cyrillic ---------------------------------------------------------------

# Fenced code, inline code and link targets stay as they are; only prose is transliterated.
_MD_PROTECTED = re.compile(r"(```.*?```|`[^`\n]*`|\]\([^)\n]*\))", re.S)


def cyrillic_readme(text: str, lexicon: dict[str, str]) -> str:
    """The Cyrillic twin of a Markdown file: prose transliterated, code and link targets kept."""
    parts = _MD_PROTECTED.split(text)
    for index in range(0, len(parts), 2):
        parts[index] = translit.to_cyrillic(parts[index], lexicon)
    return "".join(parts)


# ----- data bundles -------------------------------------------------------------------

def _keep(text):  # the Latin "transliteration"
    return text


def _text_factory(script: str, lexicon: dict[str, str]):
    if script == LAT:
        return _keep
    return lambda text: "" if text is None else translit.to_cyrillic(str(text), lexicon)


def _write_bundles(data_dir: Path, corpus: corpus_module.Corpus, script: str) -> None:
    text = _text_factory(script, corpus.lexicon)
    jsonio.dump(_index(corpus, text), data_dir / f"index.{script}.json")
    for grade in corpus.grades:
        jsonio.dump(_grade(corpus, grade, text), data_dir / f"g{grade}.{script}.json")
    for edition_id, edition in corpus.editions.items():
        jsonio.dump(_outcomes(edition, text), data_dir / "ishodi" / f"{edition_id}.{script}.json")


# In a figure, ``unit`` is a unit symbol ("cm"), not the name of a program theme.
FIGURE_KEYS = KEEP_KEYS | {"unit"}


def _deep(value, text, key=None, keep=KEEP_KEYS):
    """Transliterate every string under ``value`` except machine values (see ``keep``)."""
    if isinstance(value, str):
        return value if key in keep else text(value)
    if isinstance(value, list):
        return [_deep(item, text, key, keep) for item in value]
    if isinstance(value, dict):
        return {name: _deep(item, text, name, keep) for name, item in value.items()}
    return value


def _index(corpus: corpus_module.Corpus, text) -> dict:
    topics, units = [], {}
    for record in corpus.topic_list:
        topic_id = record.get("id")
        if not isinstance(topic_id, str) or corpus.topics.get(topic_id) is not record:
            continue  # a duplicate id: the first occurrence is the topic
        grade, unit = record.get("grade"), record.get("unit")
        topics.append({
            "id": topic_id, "grade": grade, "area": record.get("area"), "unit": text(unit),
            "kind": record.get("kind"), "name": text(record.get("name")),
        })
        if isinstance(grade, int):
            names = units.setdefault(str(grade), [])
            if unit not in names:
                names.append(unit)
    return {
        "subject": corpus.subject,
        "name": text(corpus.meta.get("name", "Matematika")),
        "grades": list(corpus.grades),
        "areas": corpus.meta.get("areas", list(AREAS)),
        "topics": topics,
        "edges": [[e.get("topic"), e.get("requires"), e.get("strength")] for e in corpus.edge_list],
        "aliases": dict(corpus.aliases),
        "units": {grade: [text(name) for name in names] for grade, names in units.items()},
        "counts": {"topics": len(topics), "edges": len(corpus.edge_list), "questions": len(corpus.questions)},
    }


def _grade(corpus: corpus_module.Corpus, grade: int, text) -> dict:
    topics = {}
    for topic_id, record in corpus.topics.items():
        if record.get("grade") != grade:
            continue
        topics[topic_id] = {
            "summary": text(record.get("summary", "")),
            "mastery": [text(item) for item in record.get("mastery", [])],
            "curriculum": _deep(record.get("curriculum", []), text),
            "review": _deep(corpus.review.get(topic_id) or None, text),
        }
    questions = {}
    for question_id, record in corpus.questions.items():
        if record.get("topic") not in topics:
            continue
        item = {key: record[key] for key in ("level", "type", "prompt", "answer", "round_to", "explanation", "points_to") if key in record}
        item["prompt"] = text(item.get("prompt", ""))
        item["explanation"] = text(item.get("explanation", ""))
        if "figure" in record:
            item["figure"] = _deep(record["figure"], text, keep=FIGURE_KEYS)
        if "choices" in record:
            item["choices"] = [{"id": choice.get("id"), "text": text(choice.get("text"))} for choice in record["choices"]]
        if record.get("type") == "numeric" and isinstance(record.get("answer"), str):
            value = parse_answer(record["answer"], canonical=True)
            if value is not None:
                item["answerRational"] = rational(value, record.get("round_to"))
        questions[question_id] = item
    return {"topics": topics, "questions": questions}


def _outcomes(edition: corpus_module.Edition, text) -> dict:
    return {
        "edition": edition.id,
        "grade": edition.grade,
        "applies_from": edition.raw.get("applies_from"),
        "themes": _deep(edition.raw.get("themes") or [], text),
        "outcomes": _deep(edition.raw.get("outcomes") or [], text),
    }
