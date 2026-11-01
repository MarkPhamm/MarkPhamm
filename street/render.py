#!/usr/bin/env python3
"""Draw Phố Commit, a street in Hanoi's Old Quarter that grows with MarkPhamm's GitHub activity.

Writes street/street.svg and rewrites the README block between the street markers.
Preview another sky with --phase dawn|day|dusk|night or --at 2026-11-01T18:00 (Hanoi time).
"""

from __future__ import annotations

import argparse
import html
import json
import math
import os
import random
import re
import subprocess
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

import requests

USER = "MarkPhamm"
REPO = f"{USER}/{USER}"
HANOI = ZoneInfo("Asia/Ho_Chi_Minh")

HERE = Path(__file__).resolve().parent
STATE_PATH = HERE / "state.json"
CONFIG_PATH = HERE / "config.json"
SVG_PATH = HERE / "street.svg"
GRAPHQL_URL = "https://api.github.com/graphql"
SEARCH_URL = "https://api.github.com/search/issues"
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

MAX_HOUSES = 8
MAX_RIDERS = 10
MAX_PARKED = 8
PARK_DAYS = 30
KEEP_DAYS = 90
FLOOR_STEPS = (10, 25, 50, 100, 200)

W, H = 1200, 560
GROUND = 400
CURB = 456
ROAD = 462
GF_H = 78
FLOOR_H = 46
POLE_TOP = 118

SANS = "-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, Menlo, Consolas, monospace"

PHASES = {
    "dawn": {
        "sky": ((0, "#46558c"), (0.22, "#8f86bd"), (0.42, "#efb2a8"), (0.7, "#fde0b6"), (1, "#fdf0d0")),
        "tint": "#8a78b0", "amount": 0.17, "lit": 0.25, "glow": 0.4,
        "far": "#b5a6cb", "near": "#9b8cba",
    },
    "day": {
        "sky": ((0, "#4c9bd4"), (0.55, "#8fc4e8"), (1, "#d6edf6")),
        "tint": "#ffffff", "amount": 0.0, "lit": 0.0, "glow": 0.0,
        "far": "#b4cbd9", "near": "#98b2c4",
    },
    "dusk": {
        "sky": ((0, "#2c2458"), (0.2, "#7c3a78"), (0.4, "#df5f5a"), (0.62, "#f7a35c"), (1, "#fbd08a")),
        "tint": "#7a3658", "amount": 0.28, "lit": 0.45, "glow": 0.75,
        "far": "#9a4f72", "near": "#76405f",
    },
    "night": {
        "sky": ((0, "#060a1d"), (0.6, "#121a3c"), (1, "#26325e")),
        "tint": "#0d1430", "amount": 0.58, "lit": 0.72, "glow": 1.0,
        "far": "#1a2347", "near": "#141b3a",
    },
}
PHASE_HOURS = (("dawn", 5, 7), ("day", 7, 17), ("dusk", 17, 19))
PHASE_WORDS = {"dawn": "dawn", "day": "daytime", "dusk": "dusk", "night": "night"}
PHASE_WHEN = {"dawn": "at dawn", "day": "during the day", "dusk": "at dusk", "night": "at night"}

PALETTE = ("#e6b450", "#a8d5bb", "#eba8a1", "#97c3dc", "#efe0c0", "#d8c47c")
SLOTS = (1, 4, 6, 2, 0, 5, 3, 7)
GREENS = ("#3f8f45", "#2f6f36", "#5aa64e", "#4c8a3c")
BLOOMS = ("#e0457b", "#f2f0e8", "#f4c542", "#d63a2f", "#c04fd0")
SHIRTS = ("#3b6ea8", "#c8442e", "#e2b34a", "#2f7d5b", "#8a5aa8", "#ece6d6", "#d96a8a", "#4a9bb0")
PANTS = ("#2b2b33", "#3b4a63", "#5a4636", "#24343a")
SKIN = ("#e2b48a", "#c99668", "#f0c9a0", "#b88458")
BIKE_COLORS = ("#c0392b", "#2c6fb0", "#26262b", "#e6e1d6", "#2f8f6b", "#d4a017", "#7a4fa3", "#8c9aa6")
AWNINGS = ("#2f7d5b", "#c8442e", "#2d6aa3", "#e0a526", "#8a5aa8")

PARK_BODY = (
    "Just hit Create. Your motorbike gets parked on Phố Commit with your username on the ticket, "
    "and it stays for 30 days. One visit per person per day, Hanoi time."
)
PHO_BODY = (
    "Just hit Create. The cart serves you a bowl of phở and the bowl counter on the street goes up by one. "
    "One visit per person per day, Hanoi time."
)


QUERY = """
query($login: String!, $yearFrom: DateTime!, $lastFrom: DateTime!, $to: DateTime!) {
  user(login: $login) {
    lastYear: contributionsCollection(from: $lastFrom, to: $to) {
      contributionCalendar { totalContributions }
    }
    thisYear: contributionsCollection(from: $yearFrom, to: $to) {
      commitContributionsByRepository(maxRepositories: 25) {
        repository { name isPrivate url owner { login } }
        contributions { totalCount }
      }
    }
  }
}
"""


def github_token() -> str:
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def fetch_github(now: datetime) -> dict:
    headers = {"Authorization": f"Bearer {github_token()}", "Accept": "application/vnd.github+json"}
    variables = {
        "login": USER,
        "yearFrom": datetime(now.year, 1, 1, tzinfo=HANOI).isoformat(),
        "lastFrom": (now - timedelta(days=365)).isoformat(),
        "to": now.isoformat(),
    }
    resp = requests.post(GRAPHQL_URL, json={"query": QUERY, "variables": variables}, headers=headers, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("errors"):
        raise RuntimeError(f"GitHub GraphQL error: {payload['errors']}")
    user = payload["data"]["user"]

    # The local gh token can see private repos, so only public ones may reach the picture.
    repos = [
        {
            "name": item["repository"]["name"],
            "owner": item["repository"]["owner"]["login"],
            "url": item["repository"]["url"],
            "commits": item["contributions"]["totalCount"],
        }
        for item in user["thisYear"]["commitContributionsByRepository"]
        if not item["repository"]["isPrivate"]
        and item["repository"]["owner"]["login"].lower() == USER.lower()
        and item["contributions"]["totalCount"] > 0
    ]
    repos.sort(key=lambda repo: (-repo["commits"], repo["name"].lower()))

    search = f"author:{USER} is:pr is:merged is:public merged:>={now.year}-01-01"
    params = {"q": search, "sort": "updated", "order": "desc", "per_page": 30}
    resp = requests.get(SEARCH_URL, params=params, headers=headers, timeout=30)
    resp.raise_for_status()
    found = resp.json()
    prs = [
        {
            "number": item["number"],
            "repo": item["repository_url"].rsplit("/", 1)[-1],
            "merged_at": (item.get("pull_request") or {}).get("merged_at") or "",
        }
        for item in found["items"]
    ]
    prs.sort(key=lambda pr: pr["merged_at"], reverse=True)

    return {
        "contributions": user["lastYear"]["contributionCalendar"]["totalContributions"],
        "repos": repos[:MAX_HOUSES],
        "merged_prs": found["total_count"],
        "prs": prs[:MAX_RIDERS],
    }


def fetch_latest_post(feed_url: str) -> dict | None:
    headers = {"User-Agent": BROWSER_UA, "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8"}
    try:
        resp = requests.get(feed_url, headers=headers, timeout=20)
        resp.raise_for_status()
        item = ET.fromstring(resp.content).find("channel/item")
        title = " ".join((item.findtext("title") or "").split())
        link = (item.findtext("link") or "").strip()
        published = parsedate_to_datetime(item.findtext("pubDate")).isoformat()
    except (requests.RequestException, ET.ParseError, AttributeError, TypeError, ValueError) as exc:
        print(f"Could not read the Substack feed, keeping the last known post: {exc}")
        return None
    if not title or not link.startswith("https://"):
        return None
    return {"title": title, "link": link, "published": published}


def load_state() -> dict:
    state = json.loads(STATE_PATH.read_text(encoding="utf-8")) if STATE_PATH.exists() else {}
    state.setdefault("parked", [])
    state.setdefault("orders", [])
    state.setdefault("bowls_served", len(state["orders"]))
    state.setdefault("last_post", None)
    return state


def save_state(state: dict, now: datetime) -> None:
    cutoff = now - timedelta(days=KEEP_DAYS)
    for key in ("parked", "orders"):
        state[key] = [entry for entry in state[key] if datetime.fromisoformat(entry["at"]) >= cutoff]
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def recent_visitors(state: dict, now: datetime) -> list[str]:
    cutoff = now - timedelta(days=PARK_DAYS)
    entries = sorted(state["parked"], key=lambda entry: datetime.fromisoformat(entry["at"]), reverse=True)
    seen, users = set(), []
    for entry in entries:
        if datetime.fromisoformat(entry["at"]) >= cutoff and entry["user"].casefold() not in seen:
            seen.add(entry["user"].casefold())
            users.append(entry["user"])
    return users


def phase_at(moment: datetime) -> str:
    hour = moment.astimezone(HANOI).hour
    for name, start, end in PHASE_HOURS:
        if start <= hour < end:
            return name
    return "night"


def floors_for(commits: int) -> int:
    return 1 + sum(commits >= step for step in FLOOR_STEPS)


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def n(value: float) -> str:
    return f"{round(value, 1):g}"


def attrs(**kw) -> str:
    parts = []
    for key, value in kw.items():
        if value is None:
            continue
        if isinstance(value, (int, float)):
            value = n(value)
        parts.append(f' {key.rstrip("_").replace("_", "-")}="{value}"')
    return "".join(parts)


def rect(x, y, w, h, fill, **kw) -> str:
    return f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" fill="{fill}"{attrs(**kw)}/>'


def circle(cx, cy, r, fill, **kw) -> str:
    return f'<circle cx="{n(cx)}" cy="{n(cy)}" r="{n(r)}" fill="{fill}"{attrs(**kw)}/>'


def ellipse(cx, cy, rx, ry, fill, **kw) -> str:
    return f'<ellipse cx="{n(cx)}" cy="{n(cy)}" rx="{n(rx)}" ry="{n(ry)}" fill="{fill}"{attrs(**kw)}/>'


def path(d, fill="none", **kw) -> str:
    return f'<path d="{d}" fill="{fill}"{attrs(**kw)}/>'


def line(x1, y1, x2, y2, stroke, width, **kw) -> str:
    return (
        f'<line x1="{n(x1)}" y1="{n(y1)}" x2="{n(x2)}" y2="{n(y2)}" stroke="{stroke}" '
        f'stroke-width="{n(width)}"{attrs(**kw)}/>'
    )


def poly(points, fill, **kw) -> str:
    coords = " ".join(f"{n(x)},{n(y)}" for x, y in points)
    return f'<polygon points="{coords}" fill="{fill}"{attrs(**kw)}/>'


def text(x, y, content, size, fill, *, cls="sans", weight=None, anchor=None, length=None, **kw) -> str:
    fit = f' textLength="{n(length)}" lengthAdjust="spacingAndGlyphs"' if length else ""
    return (
        f'<text x="{n(x)}" y="{n(y)}" class="{cls}" font-size="{n(size)}" fill="{fill}"'
        f"{attrs(font_weight=weight, text_anchor=anchor, **kw)}{fit}>{esc(content)}</text>"
    )


def group(items, **kw) -> str:
    return f"<g{attrs(**kw)}>{''.join(items)}</g>"


def rgb(color: str) -> tuple[int, int, int]:
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


def mix(a: str, b: str, t: float) -> str:
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(rgb(a), rgb(b)))


class Look:
    """Colors for one sky phase: every surface is pulled toward the phase tint, lights are not."""

    def __init__(self, phase: str):
        spec = PHASES[phase]
        self.phase = phase
        self.sky = spec["sky"]
        self.tint = spec["tint"]
        self.amount = spec["amount"]
        self.lit = spec["lit"]
        self.glow = spec["glow"]
        self.far = spec["far"]
        self.near = spec["near"]

    @property
    def dark(self) -> bool:
        return self.phase in ("dusk", "night")

    def __call__(self, color: str, strength: float = 1.0) -> str:
        return mix(color, self.tint, self.amount * strength)


_WIDE = {"M": 0.833, "W": 0.944, "m": 0.889, "w": 0.778, "@": 0.975, "\u2026": 1.0, "G": 0.778, "O": 0.778, "Q": 0.778}
_NARROW = {
    "I": 0.278, "i": 0.25, "j": 0.25, "l": 0.25, "f": 0.31, "t": 0.31, "r": 0.36, ".": 0.278, ",": 0.278,
    ":": 0.3, ";": 0.3, "'": 0.22, "\u2019": 0.25, "!": 0.3, " ": 0.278, "-": 0.333, "(": 0.333, ")": 0.333,
    "/": 0.278, "J": 0.556, "#": 0.556, "_": 0.556,
}


def text_width(value: str, size: float, *, bold: bool = False, mono: bool = False) -> float:
    if mono:
        return len(value) * 0.6 * size
    total = 0.0
    for ch in value:
        base = unicodedata.normalize("NFD", ch)[0]
        if base in _WIDE:
            total += _WIDE[base]
        elif base in _NARROW:
            total += _NARROW[base]
        elif base.isupper():
            total += 0.7
        elif base.isdigit():
            total += 0.556
        else:
            total += 0.57 if bold else 0.53
    return total * size * 1.04


def ellipsize(value: str, max_width: float, size: float, *, force: bool = False, **kw) -> str:
    if not force and text_width(value, size, **kw) <= max_width:
        return value
    while value and text_width(value.rstrip(" .,:;-_") + "\u2026", size, **kw) > max_width:
        value = value[:-1]
    return value.rstrip(" .,:;-_") + "\u2026"


def wrap(value: str, max_width: float, size: float, max_lines: int) -> list[str]:
    lines, current = [], ""
    for word in value.split():
        candidate = f"{current} {word}".strip()
        if not current or text_width(candidate, size) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = ellipsize(lines[-1], max_width, size, force=True)
    return [ellipsize(item, max_width, size) for item in lines]


def split_label(label: str) -> list[str] | None:
    best = None
    for i, ch in enumerate(label):
        if ch in "_-. " and 0 < i < len(label) - 1:
            first, second = label[:i + 1].rstrip(), label[i + 1:]
            score = max(len(first), len(second))
            if best is None or score < best[0]:
                best = (score, [first, second])
    return best[1] if best else None


def fit_sign(label: str, width: float) -> tuple[list[str], float]:
    for size in (15, 14, 13):
        if text_width(label, size, bold=True) <= width:
            return [label], size
    halves = split_label(label)
    if halves:
        for size in (13, 12, 11):
            if all(text_width(part, size, bold=True) <= width for part in halves):
                return halves, size
    return [ellipsize(label, width, 12, bold=True)], 12


def sign_need(label: str) -> float:
    one_line = text_width(label, 15, bold=True) + 30
    if one_line <= 190:
        return one_line
    halves = split_label(label)
    if halves:
        return max(text_width(part, 13, bold=True) for part in halves) + 30
    return 190


def layout_houses(repos: list[dict]) -> list[dict]:
    houses: list[dict | None] = [None] * MAX_HOUSES
    for rank, repo in enumerate(repos[:MAX_HOUSES]):
        houses[SLOTS[rank]] = {
            "name": repo["name"],
            "key": f"{repo['owner']}/{repo['name']}",
            "commits": repo["commits"],
            "floors": floors_for(repo["commits"]),
        }
    for slot in range(MAX_HOUSES):
        if houses[slot] is None:
            houses[slot] = {"name": None, "key": f"vacant-{slot}", "commits": 0, "floors": 2}

    wants = []
    for house in houses:
        need = 130 if house["name"] is None else sign_need(house["name"].upper())
        wants.append(min(max(need, 118), 196) * random.Random("width:" + house["key"]).uniform(0.95, 1.08))
    scale = W / sum(wants)
    edges = [0.0]
    for want in wants:
        edges.append(edges[-1] + want * scale)
    edges = [round(edge, 1) for edge in edges]
    edges[-1] = W

    previous = None
    for i, house in enumerate(houses):
        house["x"], house["w"] = edges[i], edges[i + 1] - edges[i]
        options = [color for color in PALETTE if color != previous]
        house["color"] = options[random.Random("color:" + house["key"]).randrange(len(options))]
        previous = house["color"]
    return houses


def place_poles(houses: list[dict]) -> tuple[float, float]:
    edges = [house["x"] for house in houses[1:]]
    left = min(edges, key=lambda edge: abs(edge - 500))
    right = min((edge for edge in edges if edge > left + 300), key=lambda edge: abs(edge - 1010), default=left + 500)
    return left, right


def cloud(x, y, s, fill, shade) -> str:
    return "".join([
        ellipse(x, y + 2 * s, 44 * s, 9 * s, shade),
        circle(x - 20 * s, y - 2 * s, 13 * s, fill),
        circle(x, y - 9 * s, 18 * s, fill),
        circle(x + 21 * s, y - 3 * s, 12 * s, fill),
        ellipse(x, y, 42 * s, 9 * s, fill),
    ])


def low_sun(houses: list[dict], east: bool) -> tuple[float, float]:
    side = [house for house in houses if (house["x"] + house["w"] / 2 > W / 2) == east]
    lowest = min(side, key=lambda house: (house["floors"], -house["w"]))
    top = GROUND - GF_H - (lowest["floors"] - 1) * FLOOR_H
    return lowest["x"] + lowest["w"] / 2, max(60, top - 62)


def draw_sky(c: Look, defs: list[str], houses: list[dict]) -> list[str]:
    stops = "".join(f'<stop offset="{offset}" stop-color="{color}"/>' for offset, color in c.sky)
    defs.append(f'<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">{stops}</linearGradient>')
    out = [rect(0, 0, W, GROUND + 4, "url(#sky)")]

    rng = random.Random("sky")
    stars = [(rng.uniform(0, W), rng.uniform(0, 300), rng.uniform(0.5, 1.5), rng.uniform(0.35, 1.0)) for _ in range(110)]
    if c.phase in ("night", "dawn"):
        fade = 1.0 if c.phase == "night" else 0.4
        for i, (x, y, r, o) in enumerate(stars):
            if c.phase == "dawn" and y > 120:
                continue
            out.append(circle(x, y, r, "#fff6dc", opacity=round(o * fade, 2), class_="twinkle" if i % 9 == 0 else None,
                              style=f"animation-delay:-{i % 5}s" if i % 9 == 0 else None))

    halo = {"day": "#fff7d6", "dawn": "#ffd2a8", "dusk": "#ffb070", "night": "#e8e6ff"}[c.phase]
    defs.append(
        f'<radialGradient id="halo"><stop offset="0" stop-color="{halo}" stop-opacity="0.75"/>'
        f'<stop offset="0.35" stop-color="{halo}" stop-opacity="0.28"/>'
        f'<stop offset="1" stop-color="{halo}" stop-opacity="0"/></radialGradient>'
    )
    if c.phase == "day":
        out += [circle(985, 62, 90, "url(#halo)"), circle(985, 62, 25, "#fff8dc")]
    elif c.phase == "dawn":
        sx, sy = low_sun(houses, east=True)
        out += [circle(sx, sy, 150, "url(#halo)"), circle(sx, sy, 30, "#fff0d0")]
    elif c.phase == "dusk":
        sx, sy = low_sun(houses, east=False)
        out += [circle(sx, sy, 170, "url(#halo)"), circle(sx, sy, 38, "#ffb46c")]
    else:
        defs.append(
            '<mask id="crescent"><circle cx="1040" cy="62" r="20" fill="#fff"/>'
            '<circle cx="1049" cy="55" r="17" fill="#000"/></mask>'
        )
        out += [circle(1040, 62, 70, "url(#halo)"), circle(1040, 62, 20, "#f6efcf", mask="url(#crescent)")]

    if c.phase == "day":
        for x, y, s in ((160, 70, 1.0), (430, 40, 0.75), (720, 82, 0.9), (1130, 120, 0.7)):
            out.append(cloud(x, y, s, "#ffffff", "#e4f0f7"))
        for x, y in ((610, 120), (628, 112), (645, 124)):
            out.append(path(f"M {x} {y} q 4 -4 8 0 q 4 -4 8 0", stroke="#33404a", stroke_width=1.4, stroke_linecap="round"))
    elif c.phase in ("dawn", "dusk"):
        tone = {"dawn": ("#f6c3b6", "#c98fa8"), "dusk": ("#f29b7c", "#a85676")}[c.phase]
        for x, y, rx in ((300, 92, 120), (640, 60, 90), (880, 120, 140), (1100, 70, 80), (520, 150, 70)):
            out.append(ellipse(x, y + 3, rx, 5, tone[1]))
            out.append(ellipse(x - 10, y, rx * 0.8, 4, tone[0]))
    else:
        for x, y, rx in ((330, 110, 110), (760, 70, 80), (980, 104, 60)):
            out.append(ellipse(x, y, rx, 2.5, "#2c3868", opacity=0.6))
            out.append(ellipse(x + rx * 0.3, y + 4, rx * 0.6, 2, "#26305c", opacity=0.6))
    return out


def draw_backdrop(c: Look) -> list[str]:
    rng = random.Random("backdrop")
    out = []
    for color, low, high, seed in ((c.far, 140, 250, 0), (c.near, 210, 300, 1)):
        x = -10.0
        while x < W:
            bw = rng.uniform(38, 92)
            top = rng.uniform(low, high)
            out.append(rect(x, top, bw + 1, GROUND - top, color))
            roll = rng.random()
            if roll < 0.28:
                tx = x + rng.uniform(6, max(7, bw - 34))
                out += [rect(tx, top - 13, 28, 11, color, rx=5.5), rect(tx + 4, top - 3, 2, 3, color), rect(tx + 22, top - 3, 2, 3, color)]
            elif roll < 0.48:
                ax = x + rng.uniform(8, bw - 8)
                out += [line(ax, top, ax, top - 22, color, 1.4), line(ax - 7, top - 16, ax + 7, top - 16, color, 1.2),
                        line(ax - 5, top - 11, ax + 5, top - 11, color, 1.2)]
            elif roll < 0.6:
                for k in range(4):
                    out.append(circle(x + rng.uniform(5, bw - 5), top - rng.uniform(0, 10), rng.uniform(9, 16), color))
            elif roll < 0.68 and seed == 0:
                mid = x + bw / 2
                out.append(path(
                    f"M {n(x - 6)} {n(top + 2)} Q {n(mid - bw * 0.3)} {n(top - 4)} {n(mid)} {n(top - 18)} "
                    f"Q {n(mid + bw * 0.3)} {n(top - 4)} {n(x + bw + 6)} {n(top + 2)} Z", color))
            for k in range(6):
                u, wx, wy = rng.random(), x + rng.uniform(4, bw - 8), rng.uniform(top + 8, GROUND - 20)
                if c.dark and u < 0.45:
                    out.append(rect(wx, wy, 3.5, 4.5, "#ffd27a", opacity=0.75 if seed else 0.55))
            x += bw
    return out


def glow(cx, cy, rx, ry, strength=1.0) -> str:
    return ellipse(cx, cy, rx, ry, "url(#winglow)", opacity=round(strength, 2))


def arch_rise(w, h) -> float:
    return min(w / 2, h * 0.28)


def pane(c: Look, x, y, w, h, lit: bool, arched: bool) -> list[str]:
    fill = "#ffd88c" if lit else c("#3b3431")
    shine = "#ffe9bb" if lit else c("#58504b")
    if arched:
        rise = arch_rise(w, h)
        shape = f"M {n(x)} {n(y + h)} L {n(x)} {n(y + rise)} A {n(w / 2)} {n(rise)} 0 0 1 {n(x + w)} {n(y + rise)} L {n(x + w)} {n(y + h)} Z"
        out = [path(shape, fill)]
    else:
        out = [rect(x, y, w, h, fill)]
    out.append(poly([(x + w * 0.15, y + h), (x + w * 0.45, y + h), (x + w * 0.85, y + h * 0.3), (x + w * 0.6, y + h * 0.3)], shine, opacity=0.55))
    return out


def shutter(c: Look, x, y, w, h) -> str:
    return rect(x, y, w, h, "url(#louver)", stroke=c("#1b4a35"), stroke_width=0.9)


def opening(c: Look, rng: random.Random, x, y, w, h, arched: bool) -> list[str]:
    lit = rng.random() < c.lit
    state = rng.choice(("open", "open", "half", "closed"))
    out = []
    if lit:
        out.append(glow(x + w / 2, y + h / 2, w * 1.15, h * 0.85, 0.9 if state != "closed" else 0.45))
    out.append(rect(x - 2, y - 2, w + 4, h + 2, c("#4a3d33")))
    out += pane(c, x, y, w, h, lit, arched)
    top = y + (arch_rise(w, h) if arched else 0)
    leaf = w / 2
    if state == "open":
        out += [shutter(c, x - leaf - 1.5, top, leaf, h - (top - y)), shutter(c, x + w + 1.5, top, leaf, h - (top - y))]
    elif state == "half":
        out += [shutter(c, x, top, leaf, h - (top - y)), shutter(c, x + w + 1.5, top, leaf, h - (top - y))]
    else:
        out += [shutter(c, x, top, leaf, h - (top - y)), shutter(c, x + leaf, top, leaf, h - (top - y))]
    return out


def potted_plant(c: Look, rng: random.Random, px, py) -> list[str]:
    pw, ph = rng.uniform(7, 10), rng.uniform(5.5, 7.5)
    out = []
    for _ in range(rng.randint(3, 5)):
        out.append(circle(px + rng.uniform(-5.5, 5.5), py - ph - rng.uniform(2, 10), rng.uniform(3, 5.2), c(rng.choice(GREENS))))
    bloom = rng.choice(BLOOMS)
    if rng.random() < 0.45:
        for _ in range(4):
            out.append(circle(px + rng.uniform(-6, 6), py - ph - rng.uniform(4, 13), 1.5, c(bloom, 0.7)))
    out.append(poly([(px - pw / 2, py - ph), (px + pw / 2, py - ph), (px + pw * 0.36, py), (px - pw * 0.36, py)], c("#b5552f")))
    out.append(rect(px - pw / 2 - 1, py - ph - 1.5, pw + 2, 2.2, c("#97411f")))
    return out


def balcony_floor(c: Look, rng: random.Random, house: dict, ft, fb, style: dict) -> list[str]:
    x, w = house["x"], house["w"]
    dw = min(w * 0.4, 62)
    dx, dy = x + (w - dw) / 2, ft + 8
    out = opening(c, rng, dx, dy, dw, fb - 5 - dy, style["arched"])
    bx, bw = max(x + 6, dx - 16), min(w - 12, dw + 32)
    bx = x + (w - bw) / 2
    if rng.random() < 0.22:
        cloth = [c(rng.choice(SHIRTS)) for _ in range(3)]
        out.append(line(dx + 2, dy + 6, dx + dw - 2, dy + 6, c("#e8e2d0"), 0.6))
        for k, color in enumerate(cloth):
            out.append(rect(dx + 5 + k * (dw - 10) / 3, dy + 6, (dw - 14) / 3, 9 + k % 2 * 3, color))
    out.append(rect(bx + 1, fb - 17, bw - 2, 13, style["rail"]))
    out.append(rect(bx, fb - 18.5, bw, 2.2, style["iron"]))
    out.append(rect(bx, fb - 4.5, bw, 4.5, c(mix(house["color"], "#ffffff", 0.45))))
    out.append(rect(bx + 2, fb, bw - 4, 2.2, c(mix(house["color"], "#2b1f14", 0.35))))
    for k in range(rng.randint(1, 3)):
        out += potted_plant(c, rng, bx + 9 + k * (bw - 18) / 2.2 + rng.uniform(-2, 2), fb - 4.5)
    if rng.random() < 0.35:
        side = bx + (6 if rng.random() < 0.5 else bw - 6)
        for k in range(14):
            yy = fb - 18 + k * 2.4 + rng.uniform(-1, 1)
            out.append(circle(side + rng.uniform(-6, 6) * (1 - k / 20), yy, rng.uniform(2, 3.4),
                              c(rng.choice(("#d8337a", "#e0457b", "#c22a6a", "#3f8f45")))))
    return out


def window_floor(c: Look, rng: random.Random, house: dict, ft, fb, style: dict) -> list[str]:
    x, w = house["x"], house["w"]
    count = 2 if w > 120 else 1
    ww, wh = min(24, w * 0.19), 27
    wy = ft + 9
    out = []
    for j in range(count):
        wx = x + w * (j + 1) / (count + 1) - ww / 2
        out += opening(c, rng, wx, wy, ww, wh, style["arched"])
        out.append(rect(wx - 4, wy + wh, ww + 8, 3, c(mix(house["color"], "#ffffff", 0.45))))
        if rng.random() < 0.4:
            out.append(rect(wx - 2, wy + wh + 3, ww + 4, 5, c("#8a5a3a")))
            for k in range(5):
                out.append(circle(wx + k * ww / 4, wy + wh + 2, 2.8, c(rng.choice(GREENS))))
    if rng.random() < 0.5:
        ax = x + (6 if rng.random() < 0.5 else w - 26)
        out += [rect(ax, fb - 19, 20, 13, c("#e9e8e2")), rect(ax, fb - 7, 20, 1.6, c("#b9b8b2")),
                circle(ax + 13, fb - 12.5, 4.5, c("#cfcec8")), circle(ax + 13, fb - 12.5, 1.5, c("#9a9993")),
                line(ax + 3, fb - 16, ax + 7, fb - 16, c("#b9b8b2"), 1), line(ax + 3, fb - 13, ax + 7, fb - 13, c("#b9b8b2"), 1)]
    return out


def roof(c: Look, rng: random.Random, house: dict, top, style: dict) -> list[str]:
    x, w, base = house["x"], house["w"], house["color"]
    kind = rng.choice(("tile", "tile", "parapet", "parapet", "terrace"))
    light = c(mix(base, "#ffffff", 0.4))
    out = []
    if kind == "tile":
        rise = rng.uniform(18, 26)
        if rng.random() < 0.6:
            vw = min(30, w * 0.25)
            vx = x + rng.uniform(14, w - vw - 14)
            out += [rect(vx, top - rise - 12, vw, rise + 6, c(base)), rect(vx + 5, top - rise - 6, vw - 10, 10, c("#3b3431")),
                    poly([(vx - 4, top - rise - 11), (vx + vw / 2, top - rise - 22), (vx + vw + 4, top - rise - 11)], c("#8c3a25"))]
        out.append(poly([(x - 3, top + 2), (x + w + 3, top + 2), (x + w - 10, top - rise), (x + 10, top - rise)], "url(#tiles)"))
        out.append(rect(x + 8, top - rise - 3, w - 16, 4, c("#7a2f1f"), rx=1.5))
        out.append(rect(x - 3, top + 1, w + 6, 3, c("#6a281a")))
    else:
        if rng.random() < 0.55:
            rw = w * rng.uniform(0.38, 0.55)
            rx = x + rng.uniform(8, w - rw - 8)
            out += [rect(rx, top - 34, rw, 34, c(mix(base, "#8a7a6a", 0.25))), rect(rx - 3, top - 37, rw + 6, 4, light),
                    rect(rx + rw * 0.3, top - 27, rw * 0.3, 14, c("#3b3431"))]
        tx = x + rng.uniform(10, w - 46)
        if rng.random() < 0.75:
            out += [rect(tx + 4, top - 22, 2.5, 9, c("#7d8287")), rect(tx + 28, top - 22, 2.5, 9, c("#7d8287")),
                    rect(tx, top - 36, 34, 15, c("#d7dde2"), rx=7.5), rect(tx + 4, top - 33, 26, 2.2, c("#f4f7f9"), rx=1.1),
                    rect(tx + 13, top - 36, 1.2, 15, c("#b9c0c6"))]
        if rng.random() < 0.6:
            ax = x + rng.uniform(10, w - 10)
            out += [line(ax, top - 14, ax, top - 46, c("#4a4a4a"), 1.3), line(ax - 9, top - 40, ax + 9, top - 40, c("#4a4a4a"), 1.1),
                    line(ax - 6, top - 34, ax + 6, top - 34, c("#4a4a4a"), 1.1)]
        if kind == "terrace":
            for k in range(int(w // 14)):
                out.append(circle(x + 8 + k * 14 + rng.uniform(-3, 3), top - 14 - rng.uniform(0, 6), rng.uniform(5, 8), c(rng.choice(GREENS))))
        out.append(rect(x, top - 14, w, 14, c(base)))
        out.append(rect(x + 6, top - 11, w - 12, 8, "url(#balusters)"))
        out.append(rect(x - 2, top - 17, w + 4, 3.5, light))
    out.append(rect(x, top, w, 3, light))
    out.append(rect(x + 2, top + 3, w - 4, 2.5, "url(#dentils)"))
    return out


def shopfront(c: Look, rng: random.Random, house: dict, style: dict) -> list[str]:
    x, w = house["x"], house["w"]
    gt = GROUND - GF_H
    vacant = house["name"] is None
    out = []
    ox, ow, oy = x + 8, w - 16, gt + 45
    oh = GROUND - oy
    u_closed, u_lit = rng.random(), rng.random()
    closed = vacant or (c.phase == "night" and u_closed < 0.3)
    shop_lit = c.dark and u_lit < 0.8
    out.append(rect(ox - 2, oy - 2, ow + 4, oh + 2, c("#3a2f28")))
    out.append(rect(ox, oy, ow, oh, "#f0c46e" if shop_lit else c("#4a3c32")))
    shelf = c("#7a5a3e") if not shop_lit else "#b9874a"
    for k in range(2):
        sy = oy + 9 + k * 11
        out.append(rect(ox + 3, sy, ow - 6, 1.6, shelf))
        gx = ox + 5
        while gx < ox + ow - 10:
            gw = rng.uniform(4, 9)
            out.append(rect(gx, sy - rng.uniform(4, 8), gw, 8, c(rng.choice(SHIRTS + BLOOMS), 0.6 if shop_lit else 1.0), opacity=0.9))
            gx += gw + rng.uniform(1, 4)
    for k in range(rng.randint(2, 4)):
        gw = rng.uniform(10, 16)
        out.append(rect(ox + 4 + k * (ow - 20) / 3.5, GROUND - 9, gw, 9, c(rng.choice(("#c79a5b", "#a8763f", "#d8b276", "#6f8fa8")))))
    shutter_h = oh if closed else oh * rng.uniform(0.18, 0.4)
    out.append(rect(ox, oy, ow, shutter_h, "url(#rollup)"))
    out.append(rect(ox - 2, oy - 4, ow + 4, 4, c("#6f7378")))

    awning = c(style["awning"])
    out.append(poly([(x + 5, gt + 38), (x + w - 5, gt + 38), (x + w - 1, gt + 47), (x + 1, gt + 47)], awning))
    for k in range(int((w - 6) // 12)):
        out.append(poly([(x + 7 + k * 12, gt + 38), (x + 12 + k * 12, gt + 38), (x + 12.5 + k * 12, gt + 47), (x + 6.5 + k * 12, gt + 47)],
                        c("#f4efe2"), opacity=0.85))
    for k in range(int((w - 2) // 8)):
        out.append(circle(x + 5 + k * 8, gt + 47, 2.6, awning))

    sx, sy, sw, sh = x + 8, gt + 5, w - 16, 31
    if vacant:
        out += [rect(sx, sy, sw, sh, c("#f2ede0", 0.5), rx=1.5), rect(sx + 2.5, sy + 2.5, sw - 5, sh - 5, "none", stroke=c("#b3261e", 0.4), stroke_width=0.9)]
        label = "CHO THUÊ"
        size = min(15, (sw - 16) / (text_width(label, 1, bold=True)))
        out.append(text(sx + sw / 2, sy + sh / 2 + size * 0.36, label, size, c("#b3261e", 0.35), weight=700, anchor="middle",
                        length=text_width(label, size, bold=True)))
        return out

    if c.dark:
        out.append(rect(sx - 4, sy - 4, sw + 8, sh + 8, "url(#signglow)"))
    out += [rect(sx, sy, sw, sh, c("#b3261e", 0.3), rx=1.5),
            rect(sx + 2.5, sy + 2.5, sw - 5, sh - 5, "none", stroke=c("#ffd54a", 0.3), stroke_width=0.8)]
    label = house["name"].upper()
    lines, size = fit_sign(label, sw - 14)
    gap = size * 1.02
    first = sy + sh / 2 - gap * (len(lines) - 1) / 2 + size * 0.36
    for k, part in enumerate(lines):
        out.append(text(sx + sw / 2, first + k * gap, part, size, c("#ffd54a", 0.3), weight=800, anchor="middle",
                        length=min(text_width(part, size, bold=True), sw - 12)))

    plate = f"{house['commits']}"
    pw = text_width(plate, 8.5, mono=True) + 7
    px, py = x + w - 12 - pw, gt - 10
    out += [rect(px, py, pw, 12, c("#1f4f8f", 0.4), rx=1.5, stroke=c("#e9eef6", 0.4), stroke_width=0.7),
            text(px + pw / 2, py + 8.8, plate, 8.5, c("#ffffff", 0.3), cls="mono", weight=700, anchor="middle")]
    return out


def draw_house(c: Look, house: dict) -> list[str]:
    # Every rng draw happens regardless of the phase, so a house keeps its shape all day.
    rng = random.Random("house:" + house["key"])
    x, w, floors, base = house["x"], house["w"], house["floors"], house["color"]
    top = GROUND - GF_H - (floors - 1) * FLOOR_H
    style = {
        "arched": rng.random() < 0.35,
        "rail": "url(#rail-light)" if rng.random() < 0.35 else "url(#rail)",
        "awning": rng.choice(AWNINGS),
    }
    style["iron"] = c("#efece2") if style["rail"] == "url(#rail-light)" else c("#2b2826")

    out = [rect(x, top, w, GROUND - top, c(base))]
    stain = c(mix(base, "#6b5a45", 0.13))
    for _ in range(4):
        sx, sw = x + rng.uniform(3, w - 20), rng.uniform(7, 18)
        sy = top + rng.uniform(4, max(5, GROUND - GF_H - top - 30))
        out.append(rect(sx, sy, sw, min(rng.uniform(26, 80), GROUND - sy), stain))
    out.append(rect(x, top, 2, GROUND - top, c(mix(base, "#2b1f14", 0.35))))
    out.append(rect(x + w - 4, top, 4, GROUND - top, c(mix(base, "#2b1f14", 0.14))))

    out += roof(c, rng, house, top, style)
    for i in range(1, floors):
        fb = GROUND - GF_H - (i - 1) * FLOOR_H
        ft = fb - FLOOR_H
        if house["name"] is None:
            out += window_floor(c, rng, house, ft, fb, style)
        elif rng.random() < (0.75 if i == 1 else 0.55):
            out += balcony_floor(c, rng, house, ft, fb, style)
        else:
            out += window_floor(c, rng, house, ft, fb, style)
        out.append(rect(x, ft - 1.5, w, 3, c(mix(base, "#ffffff", 0.35))))
    out.append(rect(x, GROUND - GF_H - 2, w, 4, c(mix(base, "#ffffff", 0.35))))
    out += shopfront(c, rng, house, style)
    return out


def wire(x1, y1, x2, y2, sag, stroke, width) -> str:
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2 + 2 * sag
    return path(f"M {n(x1)} {n(y1)} Q {n(mx)} {n(my)} {n(x2)} {n(y2)}", stroke=stroke, stroke_width=width, stroke_linecap="round")


def coil(rng: random.Random, cx, cy, r, turns, stroke) -> str:
    pts = []
    steps = int(turns * 14)
    for k in range(steps + 1):
        t = k / 14 * 2 * math.pi
        rr = r * rng.uniform(0.75, 1.15)
        pts.append((cx + rr * math.cos(t) + k * 0.35, cy + rr * 0.7 * math.sin(t) + k * 0.18))
    d = "M " + " L ".join(f"{n(px)} {n(py)}" for px, py in pts)
    return path(d, stroke=stroke, stroke_width=1.1, stroke_linejoin="round", stroke_linecap="round")


def draw_wires(c: Look, poles: tuple[float, float], houses: list[dict]) -> list[str]:
    rng = random.Random("wires")
    ink = c("#2e2b29", 0.25)
    pa, pb = poles
    out = []
    arms = [(POLE_TOP + 12, 5, 11), (POLE_TOP + 32, 4, 10)]
    for y, count, step in arms:
        for k in range(count):
            dx = -step * (count - 1) / 2 + k * step
            out.append(wire(pa + dx, y, pb + dx, y, rng.uniform(14, 34), ink, rng.uniform(0.8, 1.3)))
            out.append(wire(-10, y + rng.uniform(10, 60), pa + dx, y, rng.uniform(10, 26), ink, rng.uniform(0.8, 1.2)))
            out.append(wire(pb + dx, y, W + 10, y + rng.uniform(10, 60), rng.uniform(10, 26), ink, rng.uniform(0.8, 1.2)))
    for house in houses:
        top = GROUND - GF_H - (house["floors"] - 1) * FLOOR_H
        hx = house["x"] + rng.uniform(10, house["w"] - 10)
        hy = max(top + 20, GROUND - GF_H - rng.uniform(20, 70))
        pole = pa if abs(hx - pa) < abs(hx - pb) else pb
        if 40 < abs(hx - pole) < 190:
            out.append(wire(pole + rng.uniform(-8, 8), POLE_TOP + 32, hx, hy, rng.uniform(8, 20), ink, 0.8))
            out.append(rect(hx - 2, hy - 1, 4, 3, ink))
    for pole in poles:
        for k in range(3):
            out.append(coil(rng, pole + rng.uniform(-22, 14), POLE_TOP + rng.uniform(44, 76), rng.uniform(6, 11), rng.uniform(2.5, 4), ink))
        out.append(wire(pole + 6, POLE_TOP + 40, pole + 18, POLE_TOP + 92, 4, ink, 1.0))
    return out


def draw_lanterns(c: Look) -> list[str]:
    ink = c("#2b2522", 0.3)
    y0, ctrl = 196, 258
    out = [path(f"M -10 {y0} Q {W / 2} {ctrl} {W + 10} {y0}", stroke=ink, stroke_width=1.1)]
    count = 16
    body, rib = ("#ff5b3a", "#ffb35a") if c.dark else (c("#d42f22", 0.5), c("#a01f17", 0.5))
    gold = "#ffd36a" if c.dark else c("#e8b341", 0.5)
    for i in range(count):
        t = (i + 0.5) / count
        x = (1 - t) ** 2 * -10 + 2 * (1 - t) * t * (W / 2) + t ** 2 * (W + 10)
        y = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * ctrl + t ** 2 * y0
        items = []
        if c.glow:
            items.append(circle(x, y + 16, 22, "url(#lanternglow)", opacity=c.glow))
        items += [
            line(x, y, x, y + 5, ink, 0.8),
            rect(x - 3.5, y + 5, 7, 2.6, gold),
            ellipse(x, y + 15, 7.5, 9, body),
            path(f"M {n(x - 3)} {n(y + 7)} Q {n(x - 6)} {n(y + 15)} {n(x - 3)} {n(y + 23)} M {n(x + 3)} {n(y + 7)} "
                 f"Q {n(x + 6)} {n(y + 15)} {n(x + 3)} {n(y + 23)}", stroke=rib, stroke_width=0.8),
            rect(x - 3.5, y + 23, 7, 2.6, gold),
            line(x, y + 25.6, x, y + 32, gold, 1.2),
        ]
        out.append(group(items, class_="sway", style=f"animation-delay:-{(i * 0.7) % 4.8:.1f}s"))
    return out


def draw_pole(c: Look, x: float, plaque: bool) -> list[str]:
    rng = random.Random(f"pole:{round(x)}")
    concrete, shade, metal = c("#b5b2aa"), c("#8e8b83"), c("#3a3937")
    out = [
        poly([(x - 6, CURB - 1), (x + 6, CURB - 1), (x + 4, POLE_TOP), (x - 4, POLE_TOP)], concrete),
        poly([(x + 1.5, CURB - 1), (x + 6, CURB - 1), (x + 4, POLE_TOP), (x + 1, POLE_TOP)], shade),
        rect(x - 5, POLE_TOP - 3, 10, 4, metal, rx=1),
        rect(x - 27, POLE_TOP + 10, 54, 3.5, metal),
        rect(x - 21, POLE_TOP + 30, 42, 3, metal),
    ]
    for k in range(5):
        out.append(rect(x - 23.5 + k * 11, POLE_TOP + 6, 3, 5, c("#ebe6da")))
    for k in range(4):
        out.append(rect(x - 17.5 + k * 10, POLE_TOP + 26, 3, 5, c("#ebe6da")))
    out += [rect(x - 17, POLE_TOP + 96, 11, 18, c("#6b7a6a")), rect(x - 16, POLE_TOP + 97, 9, 1.5, c("#8a9a88"))]
    for k in range(3):
        py = 318 + k * 30 + rng.uniform(-6, 6)
        out += [rect(x - 4.5, py, 9, 13, c("#f1ece0")), rect(x - 3, py + 3, 6, 1.2, c("#c7362c", 0.5)),
                rect(x - 3, py + 6.5, 6, 1, c("#555555")), rect(x - 3, py + 9, 4, 1, c("#555555"))]
    out.append(path(f"M {n(x + 3)} {POLE_TOP + 46} Q {n(x + 26)} {POLE_TOP + 28} {n(x + 44)} {POLE_TOP + 38}",
                    stroke=metal, stroke_width=2.2))
    out.append(poly([(x + 38, POLE_TOP + 35), (x + 54, POLE_TOP + 39), (x + 52, POLE_TOP + 44), (x + 38, POLE_TOP + 41)], c("#55585c")))
    out.append(ellipse(x + 46, POLE_TOP + 43, 7, 2, "#ffe6a8" if c.dark else c("#d9dde0")))
    if plaque:
        px, py = x - 64, 250
        out += [
            rect(x - 6, py + 6, 12, 3, metal), rect(x - 6, py + 30, 12, 3, metal),
            rect(px + 2, py + 2, 128, 40, c("#0f2c55", 0.3), rx=4),
            rect(px, py, 128, 40, c("#1f4f8f", 0.3), rx=4),
            rect(px + 3, py + 3, 122, 34, "none", rx=2.5, stroke=c("#f4f1e8", 0.3), stroke_width=1),
            text(x, py + 21, "PHỐ COMMIT", 16, c("#ffffff", 0.25), weight=800, anchor="middle",
                 length=text_width("PHỐ COMMIT", 16, bold=True)),
            text(x, py + 32.5, "HOÀN KIẾM, HÀ NỘI", 7.5, c("#dfe8f5", 0.25), weight=600, anchor="middle", letter_spacing=0.8),
        ]
    return out


def draw_light_pools(c: Look, poles: tuple[float, float]) -> list[str]:
    if not c.dark:
        return []
    out = []
    for x in poles:
        lx, ly = x + 46, POLE_TOP + 44
        out += [
            ellipse(lx + 4, CURB - 8, 95, 18, "url(#pool)", opacity=c.glow),
            circle(lx, ly, 18, "url(#lanternglow)", opacity=c.glow),
        ]
    return out


def stool(c: Look, x, g, color) -> list[str]:
    body, dark = c(color), c(mix(color, "#000000", 0.25))
    return [
        poly([(x - 8, g - 11), (x + 8, g - 11), (x + 10.5, g), (x + 6.5, g), (x + 5, g - 6), (x - 5, g - 6), (x - 6.5, g), (x - 10.5, g)], body),
        rect(x - 10, g - 14, 20, 3.5, dark, rx=1.2),
        rect(x - 9.5, g - 14.5, 19, 2.5, body, rx=1.2),
    ]


def bowl(c: Look, x, y, r=5.5) -> list[str]:
    return [
        path(f"M {n(x - r)} {n(y)} Q {n(x)} {n(y + r * 1.25)} {n(x + r)} {n(y)} Z", c("#f6f3ea")),
        rect(x - r, y - 0.8, 2 * r, 1.6, c("#2e63a8", 0.6)),
        ellipse(x, y - 0.6, r - 0.8, 1, c("#c98a4a")),
    ]


def low_table(c: Look, x, g, rng: random.Random) -> list[str]:
    top, leg = c("#d7d9dc"), c("#9ea2a6")
    out = [line(x - 16, g - 18, x - 19, g, leg, 1.6), line(x + 16, g - 18, x + 19, g, leg, 1.6),
           rect(x - 24, g - 21, 48, 3.5, top, rx=1), rect(x - 24, g - 18, 48, 1.2, leg)]
    for k in range(rng.randint(1, 2)):
        out += bowl(c, x - 11 + k * 14, g - 23)
    out += [rect(x + 13, g - 31, 5, 9, c("#c79a5b")), line(x + 14, g - 34, x + 14, g - 29, c("#7a5a3e"), 0.8),
            line(x + 16.5, g - 35, x + 16.5, g - 29, c("#7a5a3e"), 0.8)]
    return out


def tea_stall(c: Look, x, g) -> list[str]:
    rng = random.Random("tea")
    out = []
    out += stool(c, x - 34, g, "#2f6db3") + stool(c, x + 36, g + 1, "#d63a2f")
    out += [line(x - 14, g - 17, x - 17, g, c("#7a5a3e"), 1.8), line(x + 14, g - 17, x + 17, g, c("#7a5a3e"), 1.8),
            rect(x - 21, g - 20, 42, 3.5, c("#9a6a42"), rx=1)]
    out += [rect(x - 15, g - 38, 10, 18, c("#c8442e"), rx=2), rect(x - 14, g - 41, 8, 3, c("#e6e1d6"), rx=1),
            rect(x - 14, g - 32, 8, 2, c("#f4c542"))]
    for k in range(3):
        gx = x + 1 + k * 6
        out += [rect(gx, g - 27, 4.5, 7, c("#f1d9a0", 0.5), opacity=0.9), rect(gx, g - 24, 4.5, 4, c("#c98a3a"), opacity=0.9)]
    out += stool(c, x + 64, g - 2, "#2f6db3")
    out += [rect(x + 54, g - 24, 22, 8, c("#c4c7ca")), rect(x + 56, g - 22, 18, 1.4, c("#e8eaec"))]
    out += potted_plant(c, rng, x + 92, g - 2)
    return out


def chalkboard(c: Look, x, g, post: dict | None) -> list[str]:
    bw, bh = 176, 66
    by = g - 84
    wood, board, chalk = c("#8b5e3c"), c("#26372f", 0.6), c("#f3efe3", 0.3)
    out = [line(x + 10, by + bh, x + 4, g, wood, 2.4), line(x + bw - 10, by + bh, x + bw - 4, g, wood, 2.4),
           rect(x - 2, by - 2, bw + 4, bh + 4, wood, rx=2), rect(x + 2, by + 2, bw - 4, bh - 4, board)]
    out.append(ellipse(x + bw / 2, by + bh / 2, bw * 0.42, bh * 0.3, c("#33463c", 0.6), opacity=0.7))
    title = post["title"] if post else "Fresh broth, new post simmering"
    lines = wrap(title, bw - 18, 12, 3)
    out.append(text(x + 9, by + 15, "Today:", 11.5, c("#f4c542", 0.3), weight=700, length=text_width("Today:", 11.5, bold=True)))
    for k, part in enumerate(lines):
        out.append(text(x + 9, by + 29 + k * 13.5, part, 12, chalk))
    return out


def pho_cart(c: Look, x, g, bowls: int) -> list[str]:
    red, wood, metal = c("#b3261e", 0.3), c("#7a4b2a"), c("#b9c0c6")
    out = []
    for wx in (x + 26, x + 106):
        out += [circle(wx, g - 13, 13, "none", stroke=c("#2a2a2a"), stroke_width=2.6), circle(wx, g - 13, 2.2, c("#555555"))]
        for k in range(6):
            a = k * math.pi / 6
            out.append(line(wx - 12 * math.cos(a), g - 13 - 12 * math.sin(a), wx + 12 * math.cos(a), g - 13 + 12 * math.sin(a), c("#777777"), 0.6))
    out += [path(f"M {n(x - 18)} {n(g - 56)} L {n(x - 4)} {n(g - 50)} L {n(x + 2)} {n(g - 34)}", stroke=metal, stroke_width=2.4)]
    out += [rect(x - 3, g - 66, 138, 4, wood), rect(x, g - 62, 132, 34, red), rect(x - 2, g - 30, 136, 4, wood),
            rect(x + 3, g - 59, 126, 28, "none", stroke=c("#ffd54a", 0.3), stroke_width=0.8)]
    out += [text(x + 40, g - 41, "PHỞ", 17, c("#ffd54a", 0.25), weight=800, anchor="middle", length=text_width("PHỞ", 17, bold=True)),
            text(x + 40, g - 33.5, "HÀ NỘI", 6.5, c("#ffd54a", 0.25), weight=700, anchor="middle", letter_spacing=1)]
    if bowls:
        headline, note = f"{bowls:,}", "bowl served" if bowls == 1 else "bowls served"
    else:
        headline, note = "ORDER", "the first bowl"
    out.append(rect(x + 72, g - 56, 56, 22, c("#f6f1e4", 0.35), rx=2))
    out.append(text(x + 100, g - 47, headline, 10, c("#b3261e", 0.3), cls="mono", weight=800, anchor="middle",
                    length=min(text_width(headline, 10, mono=True), 50)))
    out.append(text(x + 100, g - 38.5, note, 6.8, c("#3a2f28", 0.3), weight=600, anchor="middle",
                    length=min(text_width(note, 6.8, bold=True), 50)))

    if c.dark:
        out.append(ellipse(x + 46, g - 78, 70, 28, "url(#winglow)", opacity=c.glow))
    out += [rect(x + 4, g - 90, 84, 24, "#fff0c8" if c.dark else c("#dceef0", 0.5), stroke=metal, stroke_width=1.4)]
    for k in range(5):
        out.append(path(f"M {n(x + 10 + k * 7)} {n(g - 71)} q 3 -6 0 -12 q -3 -6 0 -6", stroke=c("#f1e3b8"), stroke_width=1.6))
    for k in range(4):
        out.append(circle(x + 52 + k * 6, g - 72 - (k % 2) * 3, 3.6, c(GREENS[k % 4])))
    out += [rect(x + 50, g - 82, 10, 5, c("#c9665a"), rx=1.5), rect(x + 62, g - 84, 10, 5, c("#b9554a"), rx=1.5),
            circle(x + 80, g - 72, 3, c("#9bc53d")), line(x + 8, g - 88, x + 20, g - 70, "#ffffff", 1, opacity=0.6)]
    for k in range(3):
        out += bowl(c, x + 22 + k * 1.2, g - 92 - k * 3.4, 6.5 - k * 0.4)

    out += [rect(x + 92, g - 98, 36, 34, metal), ellipse(x + 110, g - 98, 18, 4, c("#dfe4e8")),
            rect(x + 107, g - 104, 6, 3, c("#5a5f64"), rx=1), rect(x + 97, g - 92, 2, 26, c("#dfe4e8")),
            rect(x + 88, g - 88, 4, 3, c("#5a5f64")), rect(x + 128, g - 88, 4, 3, c("#5a5f64")),
            rect(x + 94, g - 64, 32, 2, c("#e85a2a") if c.dark else c("#8a8f94"))]
    for k in range(3):
        sx = x + 100 + k * 10
        out.append(path(f"M {n(sx)} {n(g - 104)} q -6 -9 0 -18 q 6 -9 0 -18", stroke="#ffffff", stroke_width=3,
                        stroke_linecap="round", opacity=0.5, class_="steam", style=f"animation-delay:-{k * 1.2:.1f}s"))
    return out


def kumquat(c: Look, rng: random.Random, x, g) -> list[str]:
    out = [rect(x - 1.2, g - 30, 2.4, 18, c("#6b4a2e"))]
    for _ in range(9):
        out.append(circle(x + rng.uniform(-11, 11), g - 34 + rng.uniform(-9, 7), rng.uniform(5, 8), c(rng.choice(GREENS))))
    for _ in range(9):
        out.append(circle(x + rng.uniform(-11, 11), g - 34 + rng.uniform(-9, 8), 1.7, c("#f28c28")))
    out += [path(f"M {n(x - 11)} {n(g - 14)} L {n(x + 11)} {n(g - 14)} L {n(x + 8)} {n(g)} L {n(x - 8)} {n(g)} Z", c("#2f5f9e")),
            rect(x - 12, g - 16, 24, 3, c("#e8eef6")), rect(x - 8, g - 9, 16, 1.4, c("#e8eef6"))]
    return out


def sleeping_cat(c: Look, x, g) -> list[str]:
    fur, dark = c("#e09a4a"), c("#b8732e")
    return [ellipse(x, g - 4, 11, 5, fur), circle(x + 9, g - 6, 4.2, fur),
            poly([(x + 6.5, g - 9), (x + 8, g - 13), (x + 10, g - 9.5)], fur), poly([(x + 10, g - 9.5), (x + 12, g - 12.5), (x + 12.5, g - 8)], fur),
            path(f"M {n(x - 10)} {n(g - 3)} Q {n(x - 4)} {n(g + 2)} {n(x + 5)} {n(g - 1)}", stroke=dark, stroke_width=2, stroke_linecap="round"),
            line(x - 4, g - 8, x - 1, g - 4, dark, 1), line(x + 1, g - 9, x + 3, g - 5, dark, 1)]


def crates(c: Look, x, g) -> list[str]:
    out = []
    for k, (dx, dy, color) in enumerate(((0, 0, "#3c8fc4"), (17, 0, "#e0a526"), (8, -12, "#d63a2f"))):
        bx, by = x + dx, g - 12 + dy
        out += [rect(bx, by, 16, 12, c(color)), rect(bx + 2, by + 2, 12, 3, c(mix(color, "#000000", 0.25))),
                rect(bx + 2, by + 7, 12, 3, c(mix(color, "#000000", 0.25)))]
    return out


def sidewalk_life(c: Look, x0: float, x1: float) -> list[str]:
    rng = random.Random("sidewalk")
    g = GROUND + 16
    span = x1 - x0
    return kumquat(c, rng, x0 + span * 0.14, g) + crates(c, x0 + span * 0.6, g) + kumquat(c, rng, x0 + span * 0.92, g)


def parking_sign(c: Look, x, g, full: bool) -> list[str]:
    out = [rect(x + 19, g - 44, 3, 44, c("#5a5f64")),
           rect(x, g - 70, 42, 28, c("#f4f0e4", 0.4), rx=2, stroke=c("#b3261e", 0.4), stroke_width=1.2),
           text(x + 21, g - 56, "GỬI XE", 10, c("#b3261e", 0.35), weight=800, anchor="middle", length=text_width("GỬI XE", 10, bold=True)),
           text(x + 21, g - 46.5, "HẾT CHỖ" if full else "CÒN CHỖ", 6.5, c("#2b2b2b", 0.35), weight=700, anchor="middle",
                length=text_width("CÒN CHỖ", 6.5, bold=True))]
    return out


def rider_figure(c: Look, rng: random.Random, dx: float) -> list[str]:
    shirt, pants, skin = c(rng.choice(SHIRTS)), c(rng.choice(PANTS)), c(rng.choice(SKIN))
    straw, straw_dark = c("#ead7a2"), c("#b89a5e")
    return [
        path(f"M {n(dx - 9)} -31 L {n(dx + 6)} -31 L {n(dx + 9)} -15", stroke=pants, stroke_width=5.5, stroke_linecap="round", stroke_linejoin="round"),
        ellipse(dx + 10.5, -14, 3.5, 1.8, c("#2a2522")),
        path(f"M {n(dx - 13)} -29 L {n(dx - 1)} -29 L {n(dx + 2)} -48 Q {n(dx - 3)} -54 {n(dx - 9)} -50 Z", shirt),
        path(f"M {n(dx - 1)} -47 L {n(dx + 8)} -41 L {n(dx + 16)} -40", stroke=shirt, stroke_width=3.4, stroke_linecap="round", stroke_linejoin="round"),
        circle(dx + 16.5, -40, 1.8, skin),
        rect(dx - 5, -55, 4, 5, skin),
        circle(dx - 3, -57, 4.6, skin),
        path(f"M {n(dx - 17)} -57 L {n(dx - 3)} -68 L {n(dx + 11)} -57 Q {n(dx - 3)} -54.5 {n(dx - 17)} -57 Z", straw, stroke=straw_dark, stroke_width=0.6),
        line(dx - 12, -60.5, dx + 6, -60.5, straw_dark, 0.5),
        line(dx - 8, -63.5, dx + 2, -63.5, straw_dark, 0.5),
    ]


def cargo(c: Look, rng: random.Random, kind: str) -> list[str]:
    if kind == "boxes":
        return [rect(-37, -45, 17, 15, c("#c79a5b")), rect(-35, -57, 14, 12, c("#d8b276")),
                line(-37, -38, -20, -38, c("#8a6a3a"), 1), line(-28.5, -57, -28.5, -30, c("#8a6a3a"), 0.8)]
    if kind == "flowers":
        out = [rect(-38, -39, 19, 9, c("#a7773f"), rx=1.5), line(-38, -35, -19, -35, c("#7d5528"), 0.8)]
        for k in range(9):
            out.append(circle(-36 + (k % 5) * 4 + rng.uniform(-1, 1), -41 - (k // 5) * 5 - rng.uniform(0, 3), 2.6,
                              c(rng.choice(BLOOMS + ("#3f8f45",)))))
        return out
    if kind == "stools":
        color = rng.choice(("#d63a2f", "#2f6db3"))
        out = []
        for k in range(5):
            out.append(poly([(-36, -30 - k * 4.2), (-22, -30 - k * 4.2), (-20, -26.5 - k * 4.2), (-38, -26.5 - k * 4.2)],
                            c(mix(color, "#000000", 0.12 * (k % 2)))))
        return out
    return []


def motorbike(c: Look, x, y, facing: int, scale: float, seed: str, *, ridden: bool, plate: str | None) -> str:
    rng = random.Random("bike:" + seed)
    body = c(rng.choice(BIKE_COLORS))
    trim = c(mix(rng.choice(BIKE_COLORS), "#000000", 0.2))
    tire, rim, metal = c("#1f1f22"), c("#8a8f96"), c("#a9aeb3")
    kind = rng.choice(("none", "none", "passenger", "boxes", "flowers", "stools"))
    parts = [ellipse(0, 0.5, 32, 2.8, "#000000", opacity=0.18)]
    for cx in (-20, 21):
        parts += [circle(cx, -9, 9, tire), circle(cx, -9, 5.6, rim), circle(cx, -9, 2, c("#3a3a3a"))]
    parts += [
        rect(-26, -11.5, 20, 3.2, metal, rx=1.6),
        rect(-6, -15, 10, 7, c("#5a5d61"), rx=1.5),
        path("M 3 -15 L 15 -15 L 17 -11 L 2 -11 Z", c("#3a3a3d")),
        path("M -31 -16 C -31 -22 -28 -25 -22 -25 L 2 -25 C 5 -25 7 -21 7 -17 L 3 -13 L -12 -13 C -14 -18 -26 -19 -29 -13 Z", body),
        path("M -27 -22 L 0 -22", stroke=trim, stroke_width=1.4),
        path("M 13 -13 C 13 -22 14 -30 17 -35 L 22 -37 C 23 -30 23 -22 20 -14 Z", body),
        path("M 13 -15 Q 21 -21 29 -15", stroke=body, stroke_width=2.6),
        line(21, -9, 19, -33, c("#6b6f75"), 2.2),
        ellipse(22, -36, 4.5, 3, body),
        ellipse(25.5, -36, 1.6, 2.2, "#fff4c8" if c.dark else c("#f3f0e0")),
        line(16, -40, 23, -39, c("#2a2a2a"), 1.8),
        line(17, -40, 15, -47, c("#2a2a2a"), 0.9),
        ellipse(15, -48, 2.2, 1.4, c("#c9ced3")),
        path("M -24 -28 C -24 -30 -20 -31 -16 -31 L 1 -30 C 3 -30 4 -28 3 -26 L -24 -26 Z", c("#2b2b2e")),
        line(-31, -29, -20, -29, metal, 1.4),
        rect(-33, -21.5, 3, 3.2, "#ff6b5a" if c.dark else c("#d8352a")),
    ]
    if c.dark and ridden:
        parts.append(circle(27, -36, 9, "url(#lanternglow)", opacity=c.glow))
    if ridden:
        if kind == "passenger":
            parts += rider_figure(c, random.Random("passenger:" + seed), -13)
        else:
            parts += cargo(c, rng, kind)
        parts += rider_figure(c, rng, 0)
    else:
        parts.append(line(-8, -10, -13, 0, c("#3a3a3a"), 1.4))
    inner = group(parts, transform=f"translate({n(x)} {n(y)}) scale({n(facing * scale)} {n(scale)})")
    if plate is None:
        return inner
    pw = text_width(plate, 8.8, mono=True) + 6
    px, py = x - facing * scale * 36 - pw / 2, y - scale * 22
    tag = [rect(px, py, pw, 11, c("#f6f3ea", 0.25), rx=1.5, stroke=c("#2a2a2a", 0.3), stroke_width=0.7),
           text(px + pw / 2, py + 8.3, plate, 8.8, c("#1d1d1f", 0.2), cls="mono", weight=700, anchor="middle")]
    return inner + "".join(tag)


def draw_riders(c: Look, prs: list[dict]) -> list[str]:
    out = []
    lanes = ((508, -1, 1.0, 70), (553, 1, 1.1, 180))
    for i, pr in enumerate(prs):
        y, facing, scale, offset = lanes[i % 2]
        x = offset + (i // 2) * 228 + random.Random(f"jitter:{pr['number']}:{pr['repo']}").uniform(-22, 22)
        bike = motorbike(c, x, y, facing, scale, f"{pr['repo']}#{pr['number']}", ridden=True, plate=f"#{pr['number']}")
        out.append(group([bike], class_="creep-r" if facing > 0 else "creep-l",
                         style=f"animation-duration:{6 + i % 4}s;animation-delay:-{i * 0.9:.1f}s"))
    return out


def draw_parked(c: Look, visitors: list[str], x0: float, x1: float) -> list[str]:
    shown = visitors[:MAX_PARKED]
    spacing = min(56.0, (x1 - x0) / MAX_PARKED)
    bikes, tags = [], []
    for i, user in enumerate(shown):
        bx = x0 + spacing * (i + 0.5)
        facing = 1 if i % 2 == 0 else -1
        bikes.append(motorbike(c, bx, CURB - 8 - (i % 2) * 6, facing, 0.88, "visitor:" + user.casefold(), ridden=False, plate=None))
        label = ellipsize("@" + user, spacing * 2 - 14, 8.6, mono=True)
        tw = text_width(label, 8.6, mono=True) + 8
        ty = 392 if i % 2 == 0 else 378
        tx = min(max(bx - tw / 2, 4), W - tw - 4)
        tags += [line(bx, ty + 12, bx + facing * 6, CURB - 8 - (i % 2) * 6 - 30, c("#5a4a3a"), 0.6),
                 rect(tx, ty, tw, 12.5, c("#fbf5e4", 0.25), rx=2, stroke=c("#9a7a4a", 0.3), stroke_width=0.7),
                 text(tx + tw / 2, ty + 9, label, 8.6, c("#2b2b2b", 0.2), cls="mono", weight=600, anchor="middle")]
    return bikes + tags


def draw_ground(c: Look) -> list[str]:
    rng = random.Random("road")
    stone, joint = c("#cdbda7"), c("#b3a08a")
    out = [rect(0, GROUND, W, CURB - GROUND, stone)]
    rows = (GROUND, GROUND + 12, GROUND + 27, GROUND + 45, CURB)
    spread = 1.25

    def at(xt, y):
        return xt + (W / 2 + (xt - W / 2) * spread - xt) * (y - GROUND) / (CURB - GROUND)

    for _ in range(34):
        col, row = rng.randrange(-4, 44), rng.randrange(4)
        x0, x1, y0, y1 = col * 30, col * 30 + 30, rows[row], rows[row + 1]
        out.append(poly([(at(x0, y0), y0), (at(x1, y0), y0), (at(x1, y1), y1), (at(x0, y1), y1)],
                        c(rng.choice(("#d6c7b2", "#c4b39c", "#c9a58a")))))
    for y in rows[1:-1]:
        out.append(rect(0, y, W, 1.1, joint))
    for col in range(-4, 45):
        out.append(line(col * 30, GROUND, at(col * 30, CURB), CURB, joint, 1))
    out += [rect(0, GROUND, W, 5, c("#8a7a68"), opacity=0.5),
            rect(0, CURB, W, 3, c("#dcd8ce")), rect(0, CURB + 3, W, ROAD - CURB - 3, c("#8f8c85")),
            rect(0, ROAD, W, H - ROAD, c("#4b4e55")), rect(0, ROAD, W, 5, c("#3c3e44"))]
    for _ in range(26):
        px, py = rng.uniform(0, W), rng.uniform(ROAD + 8, H - 6)
        out.append(ellipse(px, py, rng.uniform(10, 40), rng.uniform(1.5, 4), c(rng.choice(("#44474e", "#53565d", "#474a50")))))
    for k in range(20):
        out.append(rect(k * 64 + 10, 528, 32, 3, c("#e6e1d2", 0.6)))
    out += [ellipse(760, 545, 16, 4, c("#3a3c41")), ellipse(760, 545, 12, 2.8, c("#55585e"))]
    return out


def defs_for(c: Look) -> list[str]:
    louver, louver_dark = c("#2f7d5b"), c("#1d5840")
    iron, light_iron = c("#2b2826"), c("#efece2")
    tile, tile_dark, tile_light = c("#a9472e"), c("#7a2f1f"), c("#c4603f")
    metal, metal_dark = c("#a7abb0"), c("#80858b")
    warm = "#ffd27a"
    return [
        f'<pattern id="louver" width="8" height="3.4" patternUnits="userSpaceOnUse"><rect width="8" height="3.4" fill="{louver}"/>'
        f'<rect y="2.3" width="8" height="1.1" fill="{louver_dark}"/></pattern>',
        f'<pattern id="rail" width="5" height="20" patternUnits="userSpaceOnUse"><rect x="1.8" width="1.3" height="20" fill="{iron}"/></pattern>',
        f'<pattern id="rail-light" width="5" height="20" patternUnits="userSpaceOnUse"><rect x="1.8" width="1.3" height="20" fill="{light_iron}"/></pattern>',
        f'<pattern id="tiles" width="12" height="8" patternUnits="userSpaceOnUse"><rect width="12" height="8" fill="{tile}"/>'
        f'<rect width="12" height="1.2" fill="{tile_light}"/><rect y="3.2" width="12" height="0.9" fill="{tile_dark}"/>'
        f'<rect y="4" width="12" height="1.2" fill="{tile_light}"/><rect y="7.2" width="12" height="0.9" fill="{tile_dark}"/>'
        f'<rect width="0.9" height="4" fill="{tile_dark}"/><rect x="6" y="4" width="0.9" height="4" fill="{tile_dark}"/></pattern>',
        f'<pattern id="rollup" width="10" height="3" patternUnits="userSpaceOnUse"><rect width="10" height="3" fill="{metal}"/>'
        f'<rect y="2.1" width="10" height="0.9" fill="{metal_dark}"/></pattern>',
        f'<pattern id="dentils" width="6" height="2.5" patternUnits="userSpaceOnUse"><rect width="3" height="2.5" fill="{c("#ffffff")}" '
        'fill-opacity="0.45"/></pattern>',
        f'<pattern id="balusters" width="9" height="8" patternUnits="userSpaceOnUse"><rect width="4" height="8" fill="{c("#2b1f14")}" '
        'fill-opacity="0.3"/></pattern>',
        f'<radialGradient id="winglow"><stop offset="0" stop-color="{warm}" stop-opacity="0.55"/>'
        f'<stop offset="1" stop-color="{warm}" stop-opacity="0"/></radialGradient>',
        '<radialGradient id="lanternglow"><stop offset="0" stop-color="#ffb347" stop-opacity="0.7"/>'
        '<stop offset="1" stop-color="#ff7a2f" stop-opacity="0"/></radialGradient>',
        '<radialGradient id="signglow"><stop offset="0.5" stop-color="#ff5a3c" stop-opacity="0.35"/>'
        '<stop offset="1" stop-color="#ff5a3c" stop-opacity="0"/></radialGradient>',
        f'<radialGradient id="pool"><stop offset="0" stop-color="{warm}" stop-opacity="0.45"/>'
        f'<stop offset="1" stop-color="{warm}" stop-opacity="0"/></radialGradient>',
        f'<clipPath id="frame"><rect width="{W}" height="{H}" rx="18"/></clipPath>',
    ]


STYLE = f"""
.sans {{ font-family: {SANS}; }}
.mono {{ font-family: {MONO}; }}
@keyframes sway {{ from {{ transform: rotate(-4deg); }} to {{ transform: rotate(4deg); }} }}
@keyframes steam {{ 0% {{ transform: translateY(6px); opacity: 0; }} 35% {{ opacity: 0.55; }} 100% {{ transform: translateY(-18px); opacity: 0; }} }}
@keyframes creep-r {{ from {{ transform: translateX(-6px); }} to {{ transform: translateX(12px); }} }}
@keyframes creep-l {{ from {{ transform: translateX(6px); }} to {{ transform: translateX(-12px); }} }}
@keyframes twinkle {{ from {{ opacity: 0.2; }} to {{ opacity: 1; }} }}
@media (prefers-reduced-motion: no-preference) {{
  .sway {{ transform-box: fill-box; transform-origin: 50% 0; animation: sway 4.8s ease-in-out infinite alternate; }}
  .steam {{ animation: steam 3.6s ease-in infinite; }}
  .creep-r {{ animation: creep-r 7s ease-in-out infinite alternate; }}
  .creep-l {{ animation: creep-l 7s ease-in-out infinite alternate; }}
  .twinkle {{ animation: twinkle 2.6s ease-in-out infinite alternate; }}
}}
"""


def render_svg(data: dict, post: dict | None, bowls: int, visitors: list[str], phase: str) -> str:
    c = Look(phase)
    houses = layout_houses(data["repos"])
    poles = place_poles(houses)
    pa, pb = poles
    defs = defs_for(c)
    body: list[str] = []
    body += draw_sky(c, defs, houses)
    body += draw_backdrop(c)
    for house in houses:
        body += draw_house(c, house)
    body += draw_wires(c, poles, houses)
    body += draw_lanterns(c)
    body += draw_ground(c)
    body += draw_light_pools(c, poles)

    walk = CURB - 6
    body += sidewalk_life(c, 60, pa - 14)
    body += parking_sign(c, 10, walk, len(visitors) >= MAX_PARKED)
    body += draw_parked(c, visitors, 60, pa - 14)
    cart_x = pa + 34
    body += pho_cart(c, cart_x, walk, bowls)
    board_x = cart_x + 150
    body += chalkboard(c, board_x, walk, post)
    rng = random.Random("dining")
    dine_x = board_x + 176 + 40
    if dine_x + 40 < pb - 10:
        body += stool(c, dine_x - 30, walk, "#d63a2f") + low_table(c, dine_x, walk, rng) + stool(c, dine_x + 30, walk + 1, "#2f6db3")
        body += sleeping_cat(c, dine_x + 30, walk - 14)
    body += tea_stall(c, pb + 64, walk)
    body += draw_pole(c, pa, plaque=True) + draw_pole(c, pb, plaque=False)
    body += draw_riders(c, data["prs"])

    label = f"Phố Commit, a street in Hanoi's Old Quarter drawn from {USER}'s GitHub activity, {PHASE_WHEN[phase]}"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{esc(label)}">'
        f"<title>{esc(label)}</title><style>{STYLE}</style><defs>{''.join(defs)}</defs>"
        f'<g clip-path="url(#frame)">{"".join(body)}</g></svg>\n'
    )


def plural(count: int, word: str) -> str:
    return f"{count:,} {word}{'' if count == 1 else 's'}"


def md_text(value: str) -> str:
    return re.sub(r"([\\`*_\[\]])", r"\\\1", html.escape(value, quote=False))


def safe_link(url: str, fallback: str) -> str:
    if not re.fullmatch(r"https://[^\s<>\"']+", url or ""):
        return fallback
    return url.replace("(", "%28").replace(")", "%29")


def issue_url(title: str, body: str) -> str:
    return f"https://github.com/{REPO}/issues/new?title={quote(title, safe='')}&body={quote(body, safe='')}"


def readme_block(data: dict, post: dict | None, bowls: int, visitors: list[str], phase: str, config: dict) -> str:
    feed_home = config["substack_feed"].rsplit("/feed", 1)[0]
    name = config["substack_name"]
    sentences = [
        f"Phố Commit is a street in Hanoi's Old Quarter that grows with my GitHub activity: "
        f"{data['contributions']:,} contributions in the last year."
    ]
    if data["repos"]:
        star = next((repo for repo in data["repos"] if repo["owner"] == USER), data["repos"][0])
        sentences.append(
            "Each tube house is one of my repos, and the busier I am in it, the taller it gets: "
            f"`{star['name']}` is {plural(floors_for(star['commits']), 'floor')} after "
            f"{plural(star['commits'], 'commit')} this year."
        )
    else:
        sentences.append("Each tube house is one of my repos, and the busier I am in it, the taller it gets. "
                         "The year is young, so for now every house is for rent.")
    merged, riding = data["merged_prs"], len(data["prs"])
    if not merged:
        sentences.append("I haven't merged a pull request yet this year, so the road is quiet for now.")
    elif riding >= merged:
        sentences.append(f"I've merged {plural(merged, 'pull request')} this year, and "
                         f"{'it is' if merged == 1 else 'all of them are'} riding down the street right now.")
    else:
        sentences.append(f"I've merged {plural(merged, 'pull request')} this year, and the {riding} most recent "
                         "are riding down the street right now.")
    served = f"has served {plural(bowls, 'bowl')}" if bowls else "is waiting for its first order"
    if post:
        link = safe_link(post["link"], feed_home)
        sentences.append(f"The phở cart is serving my latest post from {md_text(name)}, "
                         f"[{md_text(post['title'])}]({link}), and {served}.")
    else:
        sentences.append(f"The phở cart is simmering until the next post from [{md_text(name)}]({feed_home}), and {served}.")
    if not visitors:
        sentences.append("Nobody has parked here this month yet, so the best spot on the sidewalk is yours.")
    else:
        sentences.append(f"{plural(len(visitors), 'visitor')} parked here this month.")
    sentences.append(f"The sky follows the time in Hanoi, where it's {PHASE_WORDS[phase]} right now.")

    alt = (
        f"Phố Commit, an illustrated street in Hanoi's Old Quarter {PHASE_WHEN[phase]}: tube houses named after my most active "
        "public repositories, motorbikes carrying my latest merged pull requests, and a phở cart serving my latest "
        "Substack post"
    )
    park = issue_url("street: park", PARK_BODY)
    pho = issue_url("street: pho", PHO_BODY)
    how = [
        "- **Houses** are my 8 public repositories with the most commits this calendar year, from the GitHub GraphQL API. "
        "The red sign is the repo name and the blue house number is its commit count.",
        "- **Floors** go up at 10, 25, 50, 100 and 200 commits, so a quiet repo still gets a one-storey house and the "
        "busiest ones top out at six.",
        "- **Motorbikes** on the road are my most recently merged pull requests in public repos this year, with the PR "
        "number on the plate.",
        f"- **The phở cart** serves the newest post from {md_text(name)}, read from its RSS feed. Every \"Order phở\" "
        "issue adds a bowl to the counter.",
        "- **Parked bikes** belong to visitors who opened a \"Park a motorbike\" issue in the last 30 days. Everyone gets "
        "one visit per day, Hanoi time.",
        "- **The sky** follows the time in Hanoi: dawn, day, dusk or night. After dark the windows and lanterns light up.",
        "- **No server.** A GitHub Action redraws the street four times a day and right after each visit, then commits "
        "one SVG to this repo. The code is in [`street/`](street).",
    ]
    return "\n".join([
        f'<p align="center"><img src="street/street.svg" width="100%" alt="{esc(alt)}"/></p>',
        "",
        " ".join(sentences),
        "",
        '<p align="center">',
        f'  <a href="{esc(park)}"><img src="https://img.shields.io/badge/Park_a_motorbike-b3261e?style=for-the-badge" alt="Park a motorbike"/></a>',
        f'  <a href="{esc(pho)}"><img src="https://img.shields.io/badge/Order_ph%E1%BB%9F-2f7d5b?style=for-the-badge" alt="Order phở"/></a>',
        "</p>",
        '<p align="center"><sub>Buttons open a pre-filled issue. Hit Create and the street updates in about a minute.</sub></p>',
        "",
        "<details>",
        "<summary>How Phố Commit works</summary>",
        "",
        *how,
        "",
        "</details>",
    ])


def update_readme(block: str) -> bool:
    import sys

    sys.path.insert(0, str(HERE.parent))
    from profile.rotate import publish

    return publish("street", block)


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--phase", choices=sorted(PHASES), help="draw this sky instead of the current Hanoi one")
    parser.add_argument("--at", help="draw the sky for this ISO datetime (naive times are Hanoi time)")
    parser.add_argument("--out", type=Path, default=SVG_PATH, help="where to write the SVG")
    parser.add_argument("--skip-readme", action="store_true", help="leave README.md untouched")
    return parser.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)
    now = datetime.now(HANOI)
    moment = now
    if args.at:
        moment = datetime.fromisoformat(args.at)
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=HANOI)
    phase = args.phase or phase_at(moment)

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    state = load_state()
    data = fetch_github(now)
    post = fetch_latest_post(config["substack_feed"])
    if post and post != state["last_post"]:
        state["last_post"] = post
        save_state(state, now)
    post = state["last_post"]
    visitors = recent_visitors(state, now)

    svg = render_svg(data, post, state["bowls_served"], visitors, phase)
    args.out.write_text(svg, encoding="utf-8")
    print(f"Drew {args.out} at {phase}: {len(data['repos'])} houses, {len(data['prs'])} riders, "
          f"{len(visitors)} parked, {state['bowls_served']} bowls, {len(svg) / 1024:.0f} KB")
    if not args.skip_readme:
        changed = update_readme(readme_block(data, post, state["bowls_served"], visitors, phase, config))
        print("README block updated." if changed else "README block unchanged.")


if __name__ == "__main__":
    main()
