#!/usr/bin/env python3
"""Print the corpus words with ``lj``, ``nj`` or ``dž`` that the digraph lexicon does not classify yet.

    python3 tools/add-digraphs.py --root .

One lowercase word per line, in Serbian alphabet order. Each is a key that still needs
its value in ``data/lint/digraphs.json``: ``"digraph"`` when the pair is one letter
(sabiranje), ``"split:<left>|<right>"`` when it is two (injekcija -> ``split:n|j``).
Rule L3 reports every such word until it is classified.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Run as a script, the package lives one directory up.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from zg.corpus import Corpus
from zg.lint import text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reči s lj, nj ili dž koje rečnik digrafa još ne klasifikuje.")
    parser.add_argument("--root", type=Path, default=None, help="koren repozitorijuma (podrazumevano: ovaj repo)")
    parser.add_argument("--subject", default="math", help="predmet u data/ (podrazumevano: math)")
    args = parser.parse_args(argv)
    corpus = Corpus.load(args.subject, root=args.root)
    for path, message in corpus.load_errors:
        print(f"{path}: {message}", file=sys.stderr)
    if corpus.load_errors:
        return 1
    for word in text.missing_from_lexicon(corpus):
        print(word)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
