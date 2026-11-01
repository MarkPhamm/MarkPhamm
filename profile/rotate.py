"""Swap the profile hero every hour, Hanoi time.

The rice terraces, the Old Quarter, and the page on its own take turns, one
hour each, then the cycle starts again. Each concept writes its hero to
<concept>/section.md; this puts the current hour's one between the profile
markers in README.md. The cover picture stays only on the hour that shows the
page on its own.
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
HANOI = ZoneInfo("Asia/Ho_Chi_Minh")
START = "<!--START_SECTION:profile-->"
END = "<!--END_SECTION:profile-->"
COVER_START = "<!--START_SECTION:cover-->"
COVER_END = "<!--END_SECTION:cover-->"
COVER = ROOT / "profile" / "cover.md"

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


def resolve(moment: datetime, show: str | None = None) -> str | None:
    """A named choice wins. Anything else, including an empty choice, follows the hour."""
    key = (show or "").strip().lower()
    if key in ("rice terraces", "terrace", "rice"):
        return "terrace"
    if key in ("old quarter", "street", "quarter"):
        return "street"
    if key in ("current page", "current", "page"):
        return None
    if key not in ("", "follow the hour", "hour"):
        raise SystemExit(f"Unknown profile {show!r}. Use rice terraces, old quarter, or current page.")
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


def cover_text(name: str | None) -> str:
    """The desk banner only belongs on the page on its own."""
    if name is not None:
        return ""
    if not COVER.exists():
        raise SystemExit(f"Missing {COVER.relative_to(ROOT)}")
    return COVER.read_text(encoding="utf-8").strip()


def splice(readme: str, start_marker: str, end_marker: str, inner: str) -> str:
    start, end = readme.find(start_marker), readme.find(end_marker)
    if start < 0 or end < start:
        raise SystemExit(f"README.md is missing the {start_marker} / {end_marker} markers")
    block = f"\n{inner}\n" if inner else "\n"
    return readme[: start + len(start_marker)] + block + readme[end:]


def apply(moment: datetime | None = None, show: str | None = None) -> bool:
    moment = moment or datetime.now(HANOI)
    name = resolve(moment, show)
    updated = splice(README.read_text(encoding="utf-8"), COVER_START, COVER_END, cover_text(name))
    updated = splice(updated, START, END, hero(name))
    if updated == README.read_text(encoding="utf-8"):
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
    parser.add_argument("--show", help="rice terraces, old quarter, or current page. Omit to follow the hour.")
    args = parser.parse_args()
    moment = moment_in(args.at)
    show = args.show if args.show is not None else os.environ.get("PROFILE_SHOW", "")
    name = resolve(moment, show)
    changed = apply(moment, show)
    shown = NAMES[name] if name else "the page on its own"
    print(f"{moment:%A %d %b %Y %H:%M} Hanoi: showing {shown}" + (" (README updated)" if changed else ""))


if __name__ == "__main__":
    main()
