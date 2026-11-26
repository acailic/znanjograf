"""Command line: ``python3 -m zg <command>``. ``all`` is the only command CI needs."""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path

from zg import corpus as corpus_module
from zg import issues as issues_module
from zg import build, jsonio, paths

# A gate is a module with ``run(corpus, issues)`` (mathcheck names it ``verify``).
GATES: dict[str, list[str]] = {
    "validate": ["zg.checks.schema", "zg.checks.graph", "zg.checks.coverage", "zg.checks.bank", "zg.checks.figure"],
    "verify": ["zg.mathcheck"],
    "lint": ["zg.lint.notation", "zg.lint.text"],
}
NOT_IMPLEMENTED = 2


def _load(module_name: str):
    """Import a module; None while it does not exist yet (a real import error still raises)."""
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        missing = exc.name or ""
        if missing == module_name or missing.startswith(module_name + ".") or missing.startswith("zg."):
            return None  # the module, or a zg module it needs, does not exist yet
        raise


def run_gate(name: str, args: argparse.Namespace) -> int:
    corpus = corpus_module.Corpus.load(args.subject, root=args.root)
    issues = issues_module.Issues()  # load errors are reported once, by zg.checks.schema
    missing = []
    for module_name in GATES[name]:
        module = _load(module_name)
        if module is None:
            missing.append(module_name)
            continue
        gate = module.verify if module_name == "zg.mathcheck" else module.run
        gate(corpus, issues)
    if missing:
        print(f"nije implementirano: {', '.join(missing)}")
        return NOT_IMPLEMENTED
    return 1 if issues.report() else 0


def run_build(args: argparse.Namespace) -> int:
    build = _load("zg.build")
    if build is None:
        print("nije implementirano: zg.build")
        return NOT_IMPLEMENTED
    if not args.check:
        build.build_site(root=args.root)
        print(f"izgrađeno: {paths.SITE_OUT if args.root is None else Path(args.root) / '_site'}")
        return 0
    differences = build.check_site(root=args.root)
    if differences:
        print("_site nije ažuriran; pokreni: python3 -m zg build")
        for line in differences:
            print(f"  {line}")
        return 1
    print("OK")
    return 0


def run_serve(args: argparse.Namespace) -> int:
    build = _load("zg.build")
    if build is None:
        print("nije implementirano: zg.build")
        return NOT_IMPLEMENTED
    build.serve(root=args.root, port=args.port)
    return 0


README_BEGIN, README_END = "<!-- zg:stats -->", "<!-- /zg:stats -->"


def _with_stats_block(text: str, block: str) -> str:
    """Put ``block`` between the markers, adding them at the end when they are missing."""
    if README_BEGIN in text and README_END in text:
        head, rest = text.split(README_BEGIN, 1)
        _, tail = rest.split(README_END, 1)
        return f"{head}{README_BEGIN}\n{block.rstrip()}\n{README_END}{tail}"
    return f"{text.rstrip()}\n\n{README_BEGIN}\n{block.rstrip()}\n{README_END}\n"


def run_report(args: argparse.Namespace) -> int:
    report = _load("zg.report")
    if report is None:
        print("nije implementirano: zg.report")
        return NOT_IMPLEMENTED
    corpus = corpus_module.Corpus.load(args.subject, root=args.root)
    if not (args.check or args.write):
        print(report.dumps_stats(corpus))
        return 0
    root = paths.ROOT if args.root is None else Path(args.root)
    readme, twin = root / "README.md", root / "README.cir.md"
    block = report.readme_block(corpus)
    if not readme.exists():
        print(f"{readme}: ne postoji; pokreni: python3 -m zg report --write")
        return 1
    if args.write:
        text = _with_stats_block(readme.read_text(encoding="utf-8"), block)
        readme.write_text(text, encoding="utf-8")
        twin.write_text(build.cyrillic_readme(text, corpus.lexicon), encoding="utf-8")
        print(f"upisano: {readme.name}, {twin.name}")
        return 0
    text = readme.read_text(encoding="utf-8")
    if not report.check_readme(text, block):
        print("README.md: brojevi u tabeli nisu tekući; pokreni: python3 -m zg report --write")
        return 1
    if not twin.exists() or twin.read_text(encoding="utf-8") != build.cyrillic_readme(text, corpus.lexicon):
        print("README.cir.md nije u skladu sa README.md; pokreni: python3 -m zg report --write")
        return 1
    print("OK")
    return 0


def run_blind(args: argparse.Namespace) -> int:
    """``blind sheet`` writes what an independent solver may see; ``blind diff`` reads what it answered."""
    blind = _load("zg.blind")
    if blind is None:
        print("nije implementirano: zg.blind")
        return NOT_IMPLEMENTED
    corpus = corpus_module.Corpus.load(args.subject, root=args.root)
    if args.action == "sheet":
        text = json.dumps(blind.make_sheet(corpus, args.grade, script=args.script, seed=args.seed), ensure_ascii=False, indent=2) + "\n"
        if args.out is None:
            print(text, end="")
        else:
            args.out.write_text(text, encoding="utf-8")
            print(f"list upisan: {args.out}")
        return 0
    try:
        answers = jsonio.load(args.answers)
    except jsonio.JsonError as exc:
        print(str(exc))
        return 1
    failures = blind.diff(corpus, args.grade, answers)
    for failure in failures:
        print(f"{failure['id']}: {', '.join(failure['reasons'])}")
    print(issues_module._summary(len(failures)))
    return 1 if failures else 0


def run_ledger(args: argparse.Namespace) -> int:
    """Record that a gate passed for one grade. ``verify`` is re-run first and must be clean."""
    ledger = _load("zg.ledger")
    if ledger is None:
        print("nije implementirano: zg.ledger")
        return NOT_IMPLEMENTED
    corpus = corpus_module.Corpus.load(args.subject, root=args.root)
    path = None if args.root is None else Path(args.root) / "data" / "ledger.json"

    def grade_of(topic_id) -> object:
        return corpus.topics.get(topic_id, {}).get("grade") if isinstance(topic_id, str) else None

    if args.gate == "edges":
        ids = [ledger.edge_id(edge) for edge in corpus.edge_list if grade_of(edge.get("topic")) == args.grade]
    else:
        ids = [qid for qid, question in corpus.questions.items() if grade_of(question.get("topic")) == args.grade]
    if args.gate == "verify":
        issues = issues_module.Issues()
        _load("zg.mathcheck").verify(corpus, issues)
        mine = [issue for issue in issues if issue.where in set(ids)]
        if mine:
            for issue in mine:
                print(issue.line())
            print(f"kapija „verify“ nije čista za {args.grade}. razred; ništa nije zabeleženo")
            return 1
    else:
        print(f"beležim da je kapija „{args.gate}“ prošla za {args.grade}. razred (odgovornost onoga ko je sproveo prolaz)")
    ledger.mark(args.gate, ids, ledger.gate_records(corpus, args.gate), path)
    print(f"zabeleženo: {len(ids)} zapisa")
    return 0


def run_status(args: argparse.Namespace) -> int:
    report = _load("zg.report")
    if report is None:
        print("nije implementirano: zg.report")
        return NOT_IMPLEMENTED
    print(report.dumps_status(corpus_module.Corpus.load(args.subject, root=args.root)))
    return 0


def _with(args: argparse.Namespace, **changes) -> argparse.Namespace:
    clone = argparse.Namespace(**vars(args))
    for key, value in changes.items():
        setattr(clone, key, value)
    return clone


def run_all(args: argparse.Namespace) -> int:
    results = [("validate", run_gate("validate", args)), ("verify", run_gate("verify", args)), ("lint", run_gate("lint", args))]
    if not args.skip_site:
        results.append(("report --check", run_report(_with(args, check=True))))
        results.append(("build --check", run_build(_with(args, check=True))))
    failed = [name for name, code in results if code != 0]
    print("SVE PROŠLO" if not failed else "PALO: " + ", ".join(failed))
    return 0 if not failed else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python3 -m zg", description="Znanjograf: provera podataka i izgradnja sajta.")
    parser.add_argument("--root", type=Path, default=None, help="koren repozitorijuma (podrazumevano: ovaj repo)")
    parser.add_argument("--subject", default="math", help="predmet u data/ (podrazumevano: math)")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "verify", "lint"):
        sub.add_parser(name)
    status = sub.add_parser("status", help="šta je provereno, a šta zastarelo, po razredu")
    status.add_argument("--skip-site", action="store_true", help="nema efekta; postoji da `all --skip-site` ima parnjaka")
    build = sub.add_parser("build", help="izgradi _site/ u oba pisma")
    build.add_argument("--check", action="store_true", help="samo proveri da li je _site/ ažuriran")
    serve = sub.add_parser("serve", help="lokalni server sa izgradnjom pri svakom zahtevu")
    serve.add_argument("--port", type=int, default=8765)
    report = sub.add_parser("report", help="statistika i blok za README")
    report.add_argument("--check", action="store_true", help="proveri da li README ima tekuće brojeve")
    report.add_argument("--write", action="store_true", help="upiši tabelu u README.md i generiši README.cir.md")
    blind = sub.add_parser("blind", help="slepi prolaz: list nezavisnom rešavaču i poređenje njegovih odgovora")
    blind_action = blind.add_subparsers(dest="action", required=True)
    sheet = blind_action.add_parser("sheet", help="samo tekstovi, bez odgovora i objašnjenja")
    sheet.add_argument("--grade", type=int, required=True)
    sheet.add_argument("--script", choices=("cyr", "lat"), default="cyr")
    sheet.add_argument("--seed", type=int, default=None)
    sheet.add_argument("--out", type=Path, default=None, help="upiši list u fajl umesto na standardni izlaz")
    difference = blind_action.add_parser("diff", help="poredi odgovore rešavača s bankom")
    difference.add_argument("--grade", type=int, required=True)
    difference.add_argument("--answers", type=Path, required=True)
    ledger = sub.add_parser("ledger", help="evidencija: zabeleži da je kapija prošla za jedan razred")
    ledger_action = ledger.add_subparsers(dest="action", required=True)
    mark = ledger_action.add_parser("mark")
    mark.add_argument("--gate", choices=("verify", "blind-solve", "classify", "cueing", "edges"), required=True)
    mark.add_argument("--grade", type=int, required=True)
    everything = sub.add_parser("all", help="sve kapije; jedina komanda koju pokreće CI")
    everything.add_argument("--skip-site", action="store_true", help="preskoči izveštaj i izgradnju (testovi)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    runners = {
        "build": run_build, "serve": run_serve, "report": run_report, "status": run_status, "all": run_all,
        "blind": run_blind, "ledger": run_ledger,
    }
    if args.command in GATES:
        return run_gate(args.command, args)
    return runners[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
