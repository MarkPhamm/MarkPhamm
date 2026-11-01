#!/usr/bin/env python3
"""Apply one visitor action from a "street: ..." issue to street/state.json and write the reply.

Reads ISSUE_TITLE, ISSUE_USER and ISSUE_NUMBER (ISSUE_BODY is accepted but unused) and writes the
markdown reply to REPLY_PATH, default reply.md. Running it twice for the same issue changes nothing.
"""

from __future__ import annotations

import os
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from render import HANOI, USER, load_state, save_state

ACTIONS = ("park", "pho")
STREET = f"https://github.com/{USER}"
LOGIN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})(?:\[bot\])?")


def plain(word: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", word) if not unicodedata.combining(ch))


def parse_action(title: str) -> tuple[str | None, str]:
    """Return (action, first word) from a title like "street: Order phở please"."""
    prefix, _, rest = title.partition(":")
    if prefix.strip().casefold() != "street":
        return None, ""
    words = re.findall(r"[^\W\d_]+", unicodedata.normalize("NFC", rest).casefold())
    for word in words:
        if plain(word) in ACTIONS:
            return plain(word), word
    return None, words[0] if words else ""


def visited_today(state: dict, user: str, now: datetime) -> bool:
    today = now.astimezone(HANOI).date()
    return any(
        entry["user"].casefold() == user.casefold()
        and datetime.fromisoformat(entry["at"]).astimezone(HANOI).date() == today
        for entry in state["parked"] + state["orders"]
    )


def visit(state: dict, title: str, user: str, number: int, now: datetime) -> tuple[str, bool]:
    """Apply the visit to state and return (reply, changed)."""
    if not LOGIN.fullmatch(user) or number <= 0:
        return "Phố Commit could not read who opened this issue, so nothing changed.", False

    action, word = parse_action(title)
    if action is None:
        shown = f" how to `{word[:20]}`" if word else " what you'd like"
        return (
            f"Sorry @{user}, Phố Commit doesn't know{shown} yet, so nothing changed on the street. "
            "Open an issue titled `street: park` to park a motorbike, or `street: pho` to order a bowl of phở."
        ), False

    if any(entry["issue"] == number for entry in state["parked"] + state["orders"]):
        return f"This visit is already on the street, @{user}. Nothing more to do.", False

    if user.casefold() != USER.casefold() and visited_today(state, user, now):
        return (
            f"You already stopped by Phố Commit today, @{user}, so this one is on the house. "
            "Come back tomorrow (Hanoi time) to park or order again."
        ), False

    entry = {"user": user, "issue": number, "at": now.astimezone(timezone.utc).isoformat(timespec="seconds")}
    if action == "park":
        state["parked"].append(entry)
        return (
            f"Your motorbike is parked on [Phố Commit]({STREET}), @{user}. Look for the ticket with your name "
            "on the sidewalk in about a minute; it stays there for 30 days. Cảm ơn for stopping by!"
        ), True

    state["orders"].append(entry)
    state["bowls_served"] += 1
    bowls = state["bowls_served"]
    reply = f"One bowl of phở for @{user}, coming right up. That makes {bowls:,} bowl{'' if bowls == 1 else 's'} served on [Phố Commit]({STREET})."
    post = state.get("last_post")
    if post and post.get("link", "").startswith("https://"):
        title = post["title"].replace("[", "(").replace("]", ")")
        reply += f" Today's special while it cools: [{title}]({post['link']})."
    return reply + " Cảm ơn!", True


def main() -> None:
    title = os.environ.get("ISSUE_TITLE", "")
    user = os.environ.get("ISSUE_USER", "")
    number = int(os.environ.get("ISSUE_NUMBER") or 0)
    reply_path = Path(os.environ.get("REPLY_PATH") or "reply.md")
    now = datetime.now(timezone.utc)

    state = load_state()
    reply, changed = visit(state, title, user, number, now)
    if changed:
        save_state(state, now)
    reply_path.write_text(reply + "\n", encoding="utf-8")
    print(reply)


if __name__ == "__main__":
    main()
