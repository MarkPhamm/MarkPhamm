"""Turn a "terrace: plant" or "terrace: feed" issue into a visit recorded in terrace/state.json.

Reads ISSUE_TITLE, ISSUE_USER and ISSUE_NUMBER (ISSUE_BODY is accepted but unused) and writes
a markdown reply to REPLY_PATH (default reply.md) for the workflow to post on the issue.
"""

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

OWNER = "MarkPhamm"
PROFILE = f"https://github.com/{OWNER}"
# Vietnam has kept UTC+7 without daylight saving time since 1975.
HANOI = timezone(timedelta(hours=7))
STATE_PATH = Path(__file__).resolve().parent / "state.json"
KEEP_DAYS = 90
LISTS = {"plant": "plantings", "feed": "feedings"}
PAST = {"plant": "planted a seedling", "feed": "fed the koi"}


def parse_action(title):
    prefix, _, rest = title.strip().partition(":")
    if prefix.strip().lower() != "terrace":
        return None
    match = re.search(r"\b(plant|feed)", rest.lower())
    return match.group(1) if match else None


def load_state():
    if not STATE_PATH.exists():
        return {"plantings": [], "feedings": []}
    state = json.loads(STATE_PATH.read_text())
    return {"plantings": state.get("plantings", []), "feedings": state.get("feedings", [])}


def save_state(state, now):
    cutoff = now - timedelta(days=KEEP_DAYS)
    for name in LISTS.values():
        state[name] = [entry for entry in state[name] if datetime.fromisoformat(entry["at"]) >= cutoff]
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")


def entries(state):
    for action, name in LISTS.items():
        for entry in state[name]:
            yield action, entry


def visit(state, action, user, number, now):
    """Apply one visit and return (reply, changed)."""
    for _, entry in entries(state):
        if entry["issue"] == number:
            return f"Issue #{number} has already been counted on the farm, so nothing changed.", False

    if action is None:
        return (
            f"Hi @{user}, the farm only knows two chores so far: `terrace: plant` and `terrace: feed`. "
            f"Try the **Plant a seedling** or **Feed the koi** button on [my profile]({PROFILE}) and hit Create.",
            False,
        )

    if user.lower() != OWNER.lower():
        today = now.date()
        for done, entry in entries(state):
            same_day = datetime.fromisoformat(entry["at"]).astimezone(HANOI).date() == today
            if same_day and entry["user"].lower() == user.lower():
                return (
                    f"Thanks for coming back, @{user}! Each visitor gets one chore a day on the farm, and you "
                    f"already {PAST[done]} today (Hanoi time). Come back tomorrow and the hill will be waiting.",
                    False,
                )

    state[LISTS[action]].append({"user": user, "issue": number, "at": now.isoformat(timespec="seconds")})
    if action == "plant":
        return (
            f"Thanks for planting, @{user}! Your seedling is in the ground, and you'll stand on "
            f"[my terraces]({PROFILE}) as a farmer in a nón lá for the next 30 days. "
            "The hill redraws in about a minute.",
            True,
        )
    fed = sum(
        1 for entry in state["feedings"]
        if datetime.fromisoformat(entry["at"]).astimezone(HANOI).date() == now.date()
    )
    times = "once" if fed == 1 else f"{fed} times"
    return (
        f"Thanks, @{user}! A handful of food lands in the paddy and the koi are already rising for it. "
        f"They've been fed {times} today. See them on [my profile]({PROFILE}) in about a minute.",
        True,
    )


def main():
    title = os.environ.get("ISSUE_TITLE", "")
    user = os.environ["ISSUE_USER"].strip()
    number = int(os.environ["ISSUE_NUMBER"])
    reply_path = Path(os.environ.get("REPLY_PATH", "reply.md"))
    now = datetime.now(HANOI)

    state = load_state()
    action = parse_action(title)
    reply, changed = visit(state, action, user, number, now)
    if changed:
        save_state(state, now)
    reply_path.write_text(reply + "\n")
    print(f"#{number} by {user}: {action or 'unknown'}, {'recorded' if changed else 'no change'}")


if __name__ == "__main__":
    main()
