"""Swap the profile hero every hour, Hanoi time.

The rice terraces, the Old Quarter, and the page on its own take turns, one
hour each, then the cycle starts again. Each concept writes its hero to
<concept>/section.md; this puts the current hour's one between the profile
markers in README.md.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
HANOI = ZoneInfo("Asia/Ho_Chi_Minh")
START = "<!--START_SECTION:profile-->"
END = "<!--END_SECTION:profile-->"

# One turn each, in this order, repeating through the day. None is the page on its own.
CYCLE = ("terrace", "street", None)

NAMES = {
    "terrace": "the rice terraces",
    "street": "the Old Quarter",
}

NOTE = (
    "The profile changes every hour: the rice terraces, then the Old Quarter, "
    "then the page on its own."
)


def moment_in(at: str | None) -> datetime:
    if not at:
        return datetime.now(HANOI)
    moment = datetime.fromisoformat(at)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=HANOI)
    return moment.astimezone(HANOI)


def active(moment: datetime) -> str | None:
    return CYCLE[moment.astimezone(HANOI).hour % len(CYCLE)]


def hero(name: str | None) -> str:
    if name is None:
        return ""
    section = ROOT / name / "section.md"
    if not section.exists():
        return ""
    body = section.read_text(encoding="utf-8").strip()
    if not body:
        return ""
    return f"<sub>{NOTE} This hour shows {NAMES[name]}.</sub>\n\n{body}"


def apply(moment: datetime | None = None) -> bool:
    moment = moment or datetime.now(HANOI)
    readme = README.read_text(encoding="utf-8")
    start, end = readme.find(START), readme.find(END)
    if start < 0 or end < start:
        raise SystemExit(f"README.md is missing the {START} / {END} markers")
    inner = hero(active(moment))
    block = f"\n{inner}\n" if inner else "\n"
    updated = readme[: start + len(START)] + block + readme[end:]
    if updated == readme:
        return False
    README.write_text(updated, encoding="utf-8")
    return True


def publish(name: str, block: str, moment: datetime | None = None) -> bool:
    path = ROOT / name / "section.md"
    text = block.strip() + "\n"
    if not path.exists() or path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8")
    return apply(moment)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--at", help="ISO datetime, read as Hanoi time when it has no offset")
    args = parser.parse_args()
    moment = moment_in(args.at)
    name = active(moment)
    changed = apply(moment)
    shown = NAMES[name] if name else "the page on its own"
    print(f"{moment:%A %d %b %Y %H:%M} Hanoi: showing {shown}" + (" (README updated)" if changed else ""))


if __name__ == "__main__":
    main()
