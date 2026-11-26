"""One shape for every problem a gate finds, so reporting is uniform everywhere."""

from __future__ import annotations

import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Issue:
    path: str  # repository-relative file path, e.g. "data/math/g1/topics.json"
    where: str  # locator, e.g. "mat-sabiranje-do-20" or "topics[2].curriculum[0]"
    code: str  # rule id, e.g. "V5-redundant"
    message: str  # Serbian Latin: what is wrong and why

    def line(self) -> str:
        return f"{self.path}: {self.where}: {self.code}: {self.message}"


class Issues(list):
    def add(self, path: str, where: str, code: str, message: str) -> None:
        self.append(Issue(str(path), str(where), code, message))

    def codes(self) -> set[str]:
        return {issue.code for issue in self}

    def report(self, stream=None) -> int:
        """Print every issue, then ``OK`` or the count. Returns the number of issues."""
        stream = sys.stdout if stream is None else stream
        for issue in sorted(self, key=lambda i: (i.path, i.where, i.code)):
            print(issue.line(), file=stream)
        print(_summary(len(self)), file=stream)
        return len(self)


def _summary(count: int) -> str:
    """``OK``, or the count with the right Serbian ending (1 greška, 2 greške, 5 grešaka, 21 greška)."""
    if count == 0:
        return "OK"
    if count % 10 == 1 and count % 100 != 11:
        word = "greška"
    elif 2 <= count % 10 <= 4 and not 12 <= count % 100 <= 14:
        word = "greške"
    else:
        word = "grešaka"
    return f"{count} {word}"
