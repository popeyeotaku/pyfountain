"""Fountain page count estimator by Troy Fullwood."""

from pathlib import Path
import sys
from math import floor
from pyfountain import FountainDoc

DEBUG = False

WIDTHS: dict[str, float] = {
    "Action": 6.0,
    "Dialogue": 3.3,
    "Character": 3.3,
    "Parenthetical": 2.0,
    "Transition": 1.5,
}

SKIPBREAKS: tuple[tuple[str, str], ...] = (
    ("Character", "Dialogue"),
    ("Character", "Parenthetical"),
    ("Dialogue", "Parenthetical"),
    ("Parenthetical", "Dialogue"),
)


def pagecount(
    fount: FountainDoc, lines_per_page: int = 55, char_per_inch: float | int = 12
) -> int:
    """Estimate the page count of the given Fountain screenplay."""
    pages = 0
    lines = 0
    prevtype: str = ""
    for elem in fount.elements:
        match etype := elem.type:
            case "Page Break":
                pages += 1
                lines = 0
                prevtype = ""
                continue
            case _:
                if etype not in WIDTHS:
                    etype = "Action"
                width = floor(WIDTHS[etype] * char_per_inch)
                lines += len(wrap(elem.text, width).splitlines())
        if prevtype and (prevtype, etype) not in SKIPBREAKS:
            lines += 1
        while lines >= lines_per_page:
            pages += 1
            lines -= lines_per_page
        prevtype = etype
    return pages


def wrap(text: str, linewidth: int) -> str:
    """Line wrap the given text."""
    out = ""
    spaceleft = linewidth
    for word in text.split():
        appended = f"{word} "
        if len(appended) > spaceleft:
            out += f"\n{word} "
            spaceleft = linewidth - len(word)
        else:
            out += appended
            spaceleft -= len(appended)
    return out.rstrip()


def main(args: list[str]):
    """Print page count from various arg files."""
    if DEBUG:
        args = ["bigfish.fountain"]
    for arg in args:
        path = Path(arg)
        print(f"{path}: {pagecount(FountainDoc(path.read_text('utf8')))}")


if __name__ == "__main__":
    main(sys.argv[1:])
