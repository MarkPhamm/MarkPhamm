"""Draw Ruộng Commit, the rice terraces on my GitHub profile, and refresh its README block.

Usage:
    python terrace/render.py                      # real data, current Hanoi time
    python terrace/render.py --phase night        # preview a sky phase today
    python terrace/render.py --at 2026-11-01T18:00 --out /tmp/terrace.svg --no-readme
"""

import argparse
import html
import json
import math
import os
import random
import subprocess
from calendar import month_abbr, month_name
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import requests

LOGIN = "MarkPhamm"
REPO_URL = f"https://github.com/{LOGIN}/{LOGIN}"
# Vietnam has kept UTC+7 without daylight saving time since 1975.
HANOI = timezone(timedelta(hours=7))

HERE = Path(__file__).resolve().parent
SVG_PATH = HERE / "terrace.svg"
STATE_PATH = HERE / "state.json"
W, H = 1200, 600
MONTHS = 12
SUMMIT_X = 770
MIN_KOI_STARS = 10
MAX_KOI = 8
MAX_FARMERS = 12
FARMER_DAYS = 30
FONT = "-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
SERIF = "Georgia, 'Times New Roman', serif"
PHASE_TIMES = {"dawn": (5, 30), "day": (11, 30), "dusk": (17, 45), "night": (23, 30)}
PHASE_WORDS = {"dawn": "dawn", "day": "daytime", "dusk": "dusk", "night": "night"}

RANGES = [(198, 124, 1.1, 0.7), (224, 104, 2.7, 0.54), (249, 86, 4.2, 0.38), (273, 68, 5.9, 0.22), (297, 46, 7.3, 0.08)]
XS = list(range(-15, W + 16, 15))
XS_ROW = list(range(-24, W + 25, 24))

PALETTES = {
    "dawn": {
        "sky": [(0, "#1c2a5e"), (0.35, "#56609c"), (0.62, "#c18fae"), (0.84, "#f6c2a2"), (1, "#ffe6b4")],
        "horizon": "#f3cdb4", "mountain": "#4b5689", "mist": "#fff1e8", "mist_alpha": 0.6,
        "paddy": "#e3c6c4", "water": ("#d9bdc0", "#4f5b84"),
        "cloud": ("#fff0e4", "#d6a3b6"), "sun": "#ffe39a", "glow": "#ffc98a",
        "tint": ("#ffc6a6", 0.1, 0.08),
    },
    "day": {
        "sky": [(0, "#3d8dd1"), (0.55, "#8fc7eb"), (1, "#e3f2f3")],
        "horizon": "#d6eaee", "mountain": "#55809e", "mist": "#ffffff", "mist_alpha": 0.7,
        "paddy": "#b3d6dc", "water": ("#a7cfd3", "#3c7480"),
        "cloud": ("#ffffff", "#d2e0eb"), "sun": "#fff6d2", "glow": "#fff1b4",
        "tint": ("#ffffff", 0.0, 0.0),
    },
    "dusk": {
        "sky": [(0, "#2a1c4e"), (0.33, "#76366c"), (0.58, "#d4545f"), (0.8, "#f5803f"), (1, "#ffb053")],
        "horizon": "#f39058", "mountain": "#4c2c57", "mist": "#ffb796", "mist_alpha": 0.5,
        "paddy": "#ec9a74", "water": ("#e58c6e", "#3f2a55"),
        "cloud": ("#ffb47f", "#b04f6f"), "sun": "#ff9442", "glow": "#ff6a35",
        "tint": ("#ff6a40", 0.17, 0.17),
    },
    "night": {
        "sky": [(0, "#050a20"), (0.6, "#101b44"), (1, "#26355f")],
        "horizon": "#2a3a64", "mountain": "#18223f", "mist": "#8a9cc6", "mist_alpha": 0.22,
        "paddy": "#2d3b63", "water": ("#26365b", "#0a142e"),
        "cloud": ("#2a3865", "#1a2448"), "sun": "#f3efd9", "glow": "#9fb4e8",
        "tint": ("#0e1838", 0.5, 0.12),
    },
}

RICE_STOPS = [(0.0, "#5fae43"), (0.4, "#8fba38"), (0.7, "#cdb434"), (1.0, "#eea92a")]
SHIRTS = ["#2f3f73", "#26262e", "#2b5d8a", "#6b4630", "#3d3550", "#1f4d4a"]
SASHES = ["#c8394f", "#e0a12f", "#3f8f5f", "#d8558a"]
FARMER_SLOTS = [
    (11, 520), (9, 300), (10, 860), (7, 610), (11, 1060), (8, 1010),
    (6, 390), (10, 170), (5, 790), (9, 690), (7, 190), (4, 540),
]
KOI_ORDER = ["kohaku", "showa", "ogon", "sanke", "tancho", "bekko", "kumonryu", "kohaku"]
KOI_BODY = (
    "M.5 0C.48-.075.36-.145.16-.148C-.04-.15-.2-.09-.33-.035L-.33.035"
    "C-.2.09-.04.15.16.148C.36.145.48.075.5 0Z"
)
KOI_TAIL = (
    "M-.31-.025C-.4-.06-.47-.16-.55-.15C-.52-.07-.49-.025-.46 0"
    "C-.49.025-.52.07-.55.15C-.47.16-.4.06-.31.025Z"
)

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    lastYear: contributionsCollection {
      contributionCalendar { totalContributions }
    }
    months: contributionsCollection(from: $from, to: $to) {
      contributionCalendar { weeks { contributionDays { date contributionCount } } }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC,
                 orderBy: {field: STARGAZERS, direction: DESC}) {
      nodes { name stargazerCount url }
    }
  }
}
"""


def github_token():
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def month_starts(moment):
    starts = []
    for back in range(MONTHS - 1, -1, -1):
        year, month = divmod(moment.year * 12 + moment.month - 1 - back, 12)
        starts.append(date(year, month + 1, 1))
    return starts


def fetch_github(moment):
    until = min(moment, datetime.now(HANOI)).astimezone(timezone.utc)
    variables = {
        "login": LOGIN,
        "from": f"{month_starts(moment)[0].isoformat()}T00:00:00Z",
        "to": until.isoformat(timespec="seconds"),
    }
    response = requests.post(
        "https://api.github.com/graphql",
        json={"query": QUERY, "variables": variables},
        headers={"Authorization": f"bearer {github_token()}"},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        raise RuntimeError(f"GitHub GraphQL errors: {payload['errors']}")
    user = payload["data"]["user"]
    weeks = user["months"]["contributionCalendar"]["weeks"]
    return {
        "last_year": user["lastYear"]["contributionCalendar"]["totalContributions"],
        "days": {day["date"]: day["contributionCount"] for week in weeks for day in week["contributionDays"]},
        "repos": [
            {"name": repo["name"], "stars": repo["stargazerCount"], "url": repo["url"]}
            for repo in user["repositories"]["nodes"]
        ],
    }


def load_state(path):
    if not path.exists():
        return {"plantings": [], "feedings": []}
    state = json.loads(path.read_text())
    return {"plantings": state.get("plantings", []), "feedings": state.get("feedings", [])}


def when(entry):
    return datetime.fromisoformat(entry["at"]).astimezone(HANOI)


def recent_planters(state, moment):
    since = moment - timedelta(days=FARMER_DAYS)
    users = {}
    for entry in sorted(state["plantings"], key=when, reverse=True):
        if when(entry) >= since:
            users.setdefault(entry["user"].lower(), entry["user"])
    return list(users.values())


def feedings_on(state, day):
    return sum(1 for entry in state["feedings"] if when(entry).date() == day)


def phase_at(moment):
    hour = moment.hour
    if 5 <= hour < 7:
        return "dawn"
    if 7 <= hour < 17:
        return "day"
    if 17 <= hour < 19:
        return "dusk"
    return "night"


def moon_phase(moment):
    synodic = 29.530588853
    known_new_moon = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
    days = (moment - known_new_moon).total_seconds() / 86400
    return (days % synodic) / synodic


def rgb(color):
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(rgb(a), rgb(b)))


def ramp(stops, t):
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            return mix(c0, c1, (t - t0) / (t1 - t0))
    return stops[-1][1]


def num(value):
    text = f"{value:.1f}"
    return text[:-2] if text.endswith(".0") else text


def line(points):
    return "M" + "L".join(f"{num(x)} {num(y)}" for x, y in points)


def shape(points):
    return line(points) + "Z"


def esc(text):
    return html.escape(str(text), quote=False).replace('"', "&quot;")


def count_words(n):
    words = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve"]
    return words[n] if n < len(words) else f"{n:,}"


def crest(x):
    width, side = (400, 272) if x < SUMMIT_X else (330, 258)
    bump = math.exp(-(((x - SUMMIT_X) / width) ** 2))
    return side - (side - 172) * bump + 4 * math.sin(x / 57 + 0.4) + 2.5 * math.sin(x / 23 + 1.3)


def hilltop(x):
    return crest(x) - 5 - 30 * math.exp(-(((x - SUMMIT_X) / 150) ** 2))


def shore(x):
    return 518 + 5 * math.sin(x / 140 + 0.3) + 3 * math.sin(x / 53 + 2)


def contour(k, x):
    t = k / MONTHS
    top, bottom = crest(x), shore(x)
    sway = (
        13 * math.sin(x / 88 + 0.6 + 0.13 * k)
        + 7 * math.sin(x / 41 + 2.2 - 0.21 * k)
        + 1.1 * math.sin(x / 19 + k * 1.7)
    )
    label_column = 0.3 + 0.7 * min(1.0, max(0.0, (x - 40) / 160))
    return top + (bottom - top) * t ** 1.05 + sway * label_column * math.sin(math.pi * t) ** 0.7


def lip(k, x):
    top, bottom = contour(k, x), contour(k + 1, x)
    share = 0.3 if k == MONTHS - 1 else 0.24
    return bottom - max(2.5, share * (bottom - top))


def ridge(x, base, amp, seed):
    rolling = 0.5 + 0.3 * math.sin(x * 0.0058 + seed) + 0.2 * math.sin(x * 0.0123 + seed * 2.3)
    peaks = (1 - abs(math.sin(x * 0.0085 + seed * 1.7))) ** 2
    detail = 0.5 + 0.5 * math.sin(x * 0.047 + seed * 3.1)
    return base - amp * (0.55 * rolling + 0.35 * peaks + 0.1 * detail)


def skyline(x):
    return min(min(ridge(x, base, amp, seed) for base, amp, seed, _ in RANGES), hilltop(x) - 18)


def sun_position(moment):
    t = min(1.0, max(0.0, (moment.hour + moment.minute / 60 - 4.5) / 15))
    x = 90 + 1020 * t
    return x, min(225 - 185 * math.sin(math.pi * t) ** 0.6, skyline(x) - 9)


def moon_position(moment):
    t = ((moment.hour + moment.minute / 60 - 19) % 24) / 10
    return 160 + 880 * t, 175 - 115 * math.sin(math.pi * t)


class Scene:
    def __init__(self, phase, moment, months, koi, planters, fed_today, last_year):
        self.phase = phase
        self.moment = moment
        self.months = months
        self.koi = koi
        self.planters = planters[:MAX_FARMERS]
        self.fed_today = fed_today
        self.last_year = last_year
        self.p = PALETTES[phase]
        self.defs = []
        self.parts = []
        self.window_spots = []
        self.farmer_tags = []

    def lit(self, color):
        tint, amount, dark = self.p["tint"]
        return mix(mix(color, tint, amount), "#000000", dark)

    def add(self, *parts):
        self.parts.extend(parts)

    def render(self):
        self.sky()
        if self.phase == "night":
            self.stars()
            self.moon()
        else:
            self.sun()
        self.clouds()
        self.mountains()
        if self.phase != "night":
            self.birds()
        self.hill()
        self.terraces()
        self.homestead()
        self.water()
        self.koi_pond()
        self.farmers()
        if self.phase in ("dusk", "night"):
            self.lamplight()
        self.labels()
        return self.document()

    def document(self):
        style = f"""
text {{ font-family: {FONT}; }}
.halo {{ stroke: rgba(30, 24, 14, .62); stroke-width: 3.2px; stroke-linejoin: round; paint-order: stroke; }}
.month {{ font-size: 14.5px; font-weight: 700; fill: #fffaf0; }}
.count {{ font-size: 11.5px; font-weight: 500; fill: #fffaf0; opacity: .82; }}
.tag {{ font-size: 13px; font-weight: 600; fill: #ffffff; }}
.koi-name {{ font-size: 12.5px; font-weight: 600; fill: #f4fbfa; }}
.title {{ font-family: {SERIF}; font-size: 28px; font-weight: 700; fill: #fffdf6; letter-spacing: .4px; }}
.subtitle {{ font-size: 13px; font-weight: 500; fill: #fffdf6; opacity: .9; }}
.legend {{ font-size: 12px; font-weight: 500; fill: #fffdf6; opacity: .92; }}
.soft {{ stroke: rgba(20, 20, 40, .35); stroke-width: 3px; stroke-linejoin: round; paint-order: stroke; }}
@media (prefers-reduced-motion: no-preference) {{
  .swim {{ animation: swim 12s ease-in-out infinite alternate; }}
  .shimmer {{ animation: shimmer 3.6s ease-in-out infinite alternate; }}
  .shimmer.late {{ animation-delay: -1.8s; }}
  .twinkle {{ animation: twinkle 2.8s ease-in-out infinite alternate; }}
  .drift {{ animation: drift 90s ease-in-out infinite alternate; }}
  .mist {{ animation: drift 46s ease-in-out infinite alternate; }}
  .ring {{ transform-box: fill-box; transform-origin: center; animation: ring 3.2s ease-out infinite; }}
  .smoke {{ animation: smoke 7s ease-in-out infinite alternate; }}
}}
@keyframes swim {{ from {{ transform: translate(-16px, -1px); }} to {{ transform: translate(16px, 2px); }} }}
@keyframes shimmer {{ from {{ opacity: .25; }} to {{ opacity: 1; }} }}
@keyframes twinkle {{ from {{ opacity: .3; }} to {{ opacity: 1; }} }}
@keyframes drift {{ from {{ transform: translateX(-24px); }} to {{ transform: translateX(24px); }} }}
@keyframes ring {{ from {{ transform: scale(.4); opacity: .9; }} to {{ transform: scale(1.4); opacity: 0; }} }}
@keyframes smoke {{ from {{ transform: translate(0, 0); opacity: .55; }} to {{ transform: translate(6px, -6px); opacity: .25; }} }}
"""
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
            f'role="img" aria-label="{esc(self.alt_text())}">\n'
            f"<title>{esc(self.alt_text())}</title>\n"
            f"<style>{style}</style>\n"
            f'<defs><clipPath id="frame"><rect width="{W}" height="{H}" rx="18"/></clipPath>\n'
            + "\n".join(self.defs)
            + '\n</defs>\n<g clip-path="url(#frame)">\n'
            + "\n".join(self.parts)
            + f'\n</g>\n<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" rx="17.5" '
            'fill="none" stroke="#000" stroke-opacity=".12" stroke-width="1.5"/>\n</svg>\n'
        )

    def alt_text(self):
        first, last = self.months[0], self.months[-1]
        farmers = len(self.planters)
        if farmers == 0:
            crowd = "no farmers are out planting yet"
        elif farmers == 1:
            crowd = "one farmer in a conical hat is planting"
        else:
            crowd = f"{count_words(farmers)} farmers in conical hats are planting"
        return (
            f"Ruộng Commit: a hillside of {MONTHS} rice terraces in Mù Cang Chải, one per month from "
            f"{month_name[first.start.month]} {first.start.year} to {month_name[last.start.month]} "
            f"{last.start.year}, ripening from green to gold with MarkPhamm's GitHub contributions. "
            f"A thatched stilt house sits on the hilltop, {count_words(len(self.koi))} koi swim in the paddy below, "
            f"{crowd}, and the sky shows {PHASE_WORDS[self.phase]} in Hanoi."
        )

    def sky(self):
        stops = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in self.p["sky"])
        self.defs.append(
            f'<linearGradient id="sky" x1="0" y1="0" x2="0" y2="330" gradientUnits="userSpaceOnUse">{stops}</linearGradient>'
        )
        mist = self.p["mist"]
        self.defs.append(
            '<linearGradient id="mistband" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{mist}" stop-opacity="0"/><stop offset=".55" stop-color="{mist}" stop-opacity="1"/>'
            f'<stop offset="1" stop-color="{mist}" stop-opacity="0"/></linearGradient>'
        )
        self.add(f'<rect width="{W}" height="{H}" fill="url(#sky)"/>')

    def halo(self, x, y, radius, color, opacity):
        gid = f"halo{len(self.defs)}"
        self.defs.append(
            f'<radialGradient id="{gid}"><stop offset="0" stop-color="{color}" stop-opacity="{opacity}"/>'
            f'<stop offset=".4" stop-color="{color}" stop-opacity="{opacity * 0.4:.3f}"/>'
            f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient>'
        )
        return f'<circle cx="{num(x)}" cy="{num(y)}" r="{radius}" fill="url(#{gid})"/>'

    def stars(self):
        rng = random.Random(7)
        steady, twinkling = [], []
        for i in range(130):
            x, y = rng.uniform(0, W), 300 * rng.random() ** 1.5
            r = rng.choice([0.6, 0.8, 1.0, 1.2, 1.6])
            dot = f'<circle cx="{num(x)}" cy="{num(y)}" r="{r}" opacity="{rng.uniform(0.45, 1):.2f}"/>'
            (twinkling if i % 4 == 0 else steady).append(dot)
        self.add(
            f'<g fill="#fffbe8">{"".join(steady)}</g>',
            f'<g fill="#fffbe8" class="twinkle">{"".join(twinkling)}</g>',
        )

    def moon(self):
        x, y = moon_position(self.moment)
        r = 21
        phase = moon_phase(self.moment)
        self.add(self.halo(x, y, 120, "#b9c8f2", 0.35))
        self.add(f'<circle cx="{num(x)}" cy="{num(y)}" r="{r}" fill="#2b3a66"/>')
        terminator = r * abs(math.cos(2 * math.pi * phase))
        waxing = phase < 0.5
        limb_sweep = 1 if waxing else 0
        bulge_sweep = 0 if (phase < 0.25 or 0.5 <= phase < 0.75) else 1
        lit_path = (
            f"M{num(x)} {num(y - r)}A{r} {r} 0 0 {limb_sweep} {num(x)} {num(y + r)}"
            f"A{num(terminator)} {r} 0 0 {bulge_sweep} {num(x)} {num(y - r)}Z"
        )
        self.defs.append(f'<clipPath id="moonlit"><path d="{lit_path}"/></clipPath>')
        self.add(
            f'<path d="{lit_path}" fill="{self.p["sun"]}"/>',
            f'<g clip-path="url(#moonlit)" fill="#c9c2a6" opacity=".45">'
            f'<circle cx="{num(x - 6)}" cy="{num(y - 5)}" r="5"/><circle cx="{num(x + 7)}" cy="{num(y + 4)}" r="6.5"/>'
            f'<circle cx="{num(x - 3)}" cy="{num(y + 10)}" r="3"/></g>',
        )

    def sun(self):
        x, y = sun_position(self.moment)
        radius = 24 if self.phase == "day" else 30
        self.add(self.halo(x, y, 170, self.p["glow"], 0.7))
        self.add(
            f'<circle cx="{num(x)}" cy="{num(y)}" r="{radius}" fill="{self.p["sun"]}"/>',
            f'<circle cx="{num(x - 5)}" cy="{num(y - 5)}" r="{radius * 0.62:.1f}" fill="#fff" opacity=".28"/>',
        )

    def clouds(self):
        top, shade = self.p["cloud"]
        spots = [(250, 112, 1.0), (565, 66, 0.6), (870, 128, 1.15), (1010, 96, 0.7)]
        if self.phase == "night":
            spots = [(330, 128, 0.9), (930, 112, 1.1)]
        blobs = [(-34, 0, 15), (-14, -10, 19), (10, -15, 22), (33, -5, 17), (50, 1, 11)]
        group = []
        for cx, cy, s in spots:
            shadow = "".join(
                f'<circle cx="{num(cx + bx * s)}" cy="{num(cy + by * s + 3 * s)}" r="{num(br * s)}"/>' for bx, by, br in blobs
            )
            body = "".join(
                f'<circle cx="{num(cx + bx * s)}" cy="{num(cy + by * s)}" r="{num(br * s)}"/>' for bx, by, br in blobs
            )
            base = (
                f'<rect x="{num(cx - 48 * s)}" y="{num(cy - 2 * s)}" width="{num(104 * s)}" height="{num(12 * s)}" '
                f'rx="{num(6 * s)}"/>'
            )
            group.append(f'<g fill="{shade}">{shadow}{base}</g><g fill="{top}">{body}</g>')
        opacity = 0.4 if self.phase == "night" else 0.95
        self.add(f'<g class="drift" opacity="{opacity}">{"".join(group)}</g>')

    def birds(self):
        flock = [(352, 158, 1.0), (370, 149, 0.8), (386, 162, 0.9), (402, 152, 0.7), (640, 118, 0.8), (656, 126, 0.65)]
        wings = "".join(
            f"M{num(x)} {num(y)}q{num(3 * s)} {num(-4 * s)} {num(6 * s)} 0q{num(3 * s)} {num(-4 * s)} {num(6 * s)} 0"
            for x, y, s in flock
        )
        color = mix(self.p["mountain"], "#000000", 0.35)
        self.add(f'<path d="{wings}" fill="none" stroke="{color}" stroke-width="1.4" stroke-linecap="round" class="drift"/>')

    def mountains(self):
        mist, alpha = self.p["mist"], self.p["mist_alpha"]
        for i, (base, amp, seed, haze) in enumerate(RANGES):
            color = mix(self.p["mountain"], self.p["horizon"], haze)
            foot = mix(color, mist, 0.45)
            self.defs.append(
                f'<linearGradient id="range{i}" x1="0" y1="{base - amp}" x2="0" y2="{base + 18}" gradientUnits="userSpaceOnUse">'
                f'<stop offset="0" stop-color="{color}"/><stop offset=".6" stop-color="{color}"/>'
                f'<stop offset="1" stop-color="{foot}"/></linearGradient>'
            )
            points = [(x, ridge(x, base, amp, seed)) for x in range(-12, W + 13, 6)]
            self.add(f'<path d="{line(points)}L{W + 12} 400L-12 400Z" fill="url(#range{i})"/>')
            self.add(f'<rect x="0" y="{base - 6}" width="{W}" height="34" fill="url(#mistband)" opacity="{alpha:.2f}"/>')
        wisps = [(180, 286, 230, 9), (620, 252, 300, 8), (1010, 276, 260, 10), (400, 226, 200, 7)]
        self.add(
            f'<g class="mist" fill="{mist}" opacity="{alpha:.2f}">'
            + "".join(f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}"/>' for x, y, rx, ry in wisps)
            + "</g>"
        )

    def hill(self):
        top = [(x, hilltop(x)) for x in XS]
        self.add(f'<path d="{line(top)}L{W + 12} 360L-12 360Z" fill="{self.lit("#4a7a39")}"/>')
        self.add(
            f'<path d="{line(top)}" fill="none" stroke="{self.lit("#6c9a4c")}" stroke-width="2" opacity=".7"/>'
        )
        rng = random.Random(11)
        clusters = [(-10, 150), (300, 420), (560, 665), (880, 990), (1080, 1210)]
        trees = []
        for start, stop in clusters:
            x = start
            while x < stop:
                trees.append((x, rng.uniform(6, 12), rng.random() < 0.3, rng.random()))
                x += rng.uniform(9, 17)
        trees.sort(key=lambda tree: tree[1])
        for x, size, conifer, tone in trees:
            self.add(self.tree(x, hilltop(x) + 3, size, conifer, tone))

    def tree(self, x, ground, size, conifer, tone):
        dark = self.lit(mix("#244a28", "#35602f", tone))
        light = self.lit(mix("#3f7334", "#5a8f42", tone))
        trunk = self.lit("#4a3424")
        if conifer:
            h = size * 3
            return (
                f'<rect x="{num(x - 1)}" y="{num(ground - 4)}" width="2" height="4" fill="{trunk}"/>'
                f'<path d="M{num(x)} {num(ground - h)}L{num(x + size * 0.9)} {num(ground - 3)}L{num(x - size * 0.9)} {num(ground - 3)}Z" fill="{dark}"/>'
                f'<path d="M{num(x)} {num(ground - h)}L{num(x - size * 0.9)} {num(ground - 3)}L{num(x - size * 0.15)} {num(ground - 3)}Z" fill="{light}" opacity=".55"/>'
            )
        cy = ground - size * 1.1
        return (
            f'<rect x="{num(x - 1.2)}" y="{num(ground - size * 0.6)}" width="2.4" height="{num(size * 0.6)}" fill="{trunk}"/>'
            f'<circle cx="{num(x)}" cy="{num(cy)}" r="{num(size)}" fill="{dark}"/>'
            f'<circle cx="{num(x - size * 0.3)}" cy="{num(cy - size * 0.32)}" r="{num(size * 0.58)}" fill="{light}"/>'
        )

    def terraces(self):
        # Bands run down to the canvas floor and rely on being painted top to bottom, so each
        # contour is stored once and reused for fills, clips and strokes.
        floor = f"L{W + 15} {H + 20}L-15 {H + 20}Z"
        for k in range(MONTHS):
            self.defs.append(f'<path id="c{k}" d="{line([(x, contour(k, x)) for x in XS])}{floor}"/>')
            self.defs.append(f'<path id="l{k}" d="{line([(x, lip(k, x)) for x in XS])}{floor}"/>')
            self.defs.append(f'<clipPath id="paddy{k}"><use href="#c{k}"/></clipPath>')
        mud, seam, grass = self.lit("#b38c5c"), self.lit("#3a2c1c"), self.lit("#2f3d1c")
        for k, month in enumerate(self.months):
            r = month.ripeness
            rice = self.lit(ramp(RICE_STOPS, r))
            self.add(f'<use href="#c{k}" fill="{mix(self.p["paddy"], rice, 0.25 + 0.75 * min(1.0, r / 0.2))}"/>')
            if r < 0.12:
                self.seedlings(k, rice)
            else:
                self.rice_rows(k, rice, r)
            self.paddies(k, mud)
            self.add(f'<use href="#l{k}" fill="{self.lit(mix(ramp(RICE_STOPS, r * 0.6), "#3b3f1e", 0.5))}"/>')
            middle = [(x, (lip(k, x) + contour(k + 1, x)) / 2) for x in XS_ROW]
            depth = sum(contour(k + 1, x) - lip(k, x) for x in XS_ROW) / len(XS_ROW)
            self.add(
                f'<path d="{line(middle)}" fill="none" stroke="{grass}" stroke-width="{num(depth * 0.55)}" '
                f'stroke-dasharray="1.2 2.4 .8 3.1" opacity=".55"/>',
                f'<use href="#l{k}" fill="none" stroke="{mud}" stroke-width="1.8"/>',
            )
            if k:
                self.add(f'<use href="#c{k}" fill="none" stroke="{seam}" stroke-width="1.1" opacity=".55"/>')
        self.defs.append(
            f'<linearGradient id="relief" x1="0" x2="{W}" y1="0" y2="0" gradientUnits="userSpaceOnUse">'
            f'<stop offset="0" stop-color="#fff" stop-opacity=".04"/>'
            f'<stop offset="{SUMMIT_X / W:.3f}" stop-color="#fff" stop-opacity="0"/>'
            f'<stop offset="1" stop-color="#000" stop-opacity=".13"/></linearGradient>'
        )
        self.defs.append(
            f'<linearGradient id="haze" x1="0" y1="165" x2="0" y2="430" gradientUnits="userSpaceOnUse">'
            f'<stop offset="0" stop-color="{self.p["horizon"]}" stop-opacity=".18"/>'
            f'<stop offset="1" stop-color="{self.p["horizon"]}" stop-opacity="0"/></linearGradient>'
        )
        self.add('<use href="#c0" fill="url(#relief)"/>', '<use href="#c0" fill="url(#haze)"/>')

    def paddies(self, k, mud):
        rng = random.Random(100 + k)
        tones, bunds = [], []
        x = rng.uniform(-60, 20)
        while x < W:
            step = rng.uniform(70, 170)
            near, far = x + rng.uniform(-5, 5), x + step
            tones.append(
                f'<path d="{shape([(x, contour(k, x) - 8), (far, contour(k, far) - 8), (far, lip(k, far) + 8), (near, lip(k, near) + 8)])}" '
                f'fill="{rng.choice(["#fff", "#000"])}" opacity="{rng.uniform(0.03, 0.08):.2f}"/>'
            )
            bunds.append(f"M{num(x)} {num(contour(k, x))}L{num(near)} {num(lip(k, near))}")
            x = far
        self.add(
            f'<g clip-path="url(#paddy{k})">{"".join(tones)}'
            f'<path d="{"".join(bunds)}" stroke="{mud}" stroke-width="1.5" opacity=".85"/></g>'
        )

    def rice_rows(self, k, rice, r):
        thickness = sum(lip(k, x) - contour(k, x) for x in XS_ROW) / len(XS_ROW)
        rows = max(2, round(thickness / 5.5))
        width = thickness / rows * 0.8
        zoom = 0.8 + 0.5 * k / (MONTHS - 1)
        dark_dash = " ".join(num(v * zoom) for v in (1.3, 3.1, 1.1, 4, 1.5, 2.8))
        light_dash = " ".join(num(v * zoom) for v in (0.9, 4.6, 1, 3.7))
        dark = mix(rice, "#2c4818", 0.36)
        light = mix(rice, "#fff2b8", 0.3 + 0.15 * r)
        group = []
        for j in range(rows):
            f = (j + 0.6) / rows
            points = [(x, contour(k, x) + (lip(k, x) - contour(k, x)) * f) for x in XS_ROW]
            self.defs.append(f'<path id="r{k}_{j}" d="{line(points)}"/>')
            group.append(
                f'<use href="#r{k}_{j}" stroke="{dark}" stroke-width="{num(width)}" stroke-dasharray="{dark_dash}" '
                f'stroke-dashoffset="{num(j * 2.3)}"/>'
                f'<use href="#r{k}_{j}" stroke="{light}" stroke-width="{num(width * 0.5)}" stroke-dasharray="{light_dash}" '
                f'stroke-dashoffset="{num(j * 1.7 + 2)}" transform="translate(0 {num(-width * 0.25)})"/>'
            )
        self.add(f'<g clip-path="url(#paddy{k})" fill="none">{"".join(group)}</g>')

    def seedlings(self, k, rice):
        rng = random.Random(k)
        thickness = sum(lip(k, x) - contour(k, x) for x in XS_ROW) / len(XS_ROW)
        rows = max(2, round(thickness / 7))
        tufts, shine = [], []
        for j in range(rows):
            f = (j + 0.7) / (rows + 0.3)
            x = rng.uniform(-6, 6)
            while x < W + 8:
                y = contour(k, x) + (lip(k, x) - contour(k, x)) * f
                h = 3.2 + 0.7 * j
                tufts.append(f"M{num(x)} {num(y)}l-1.6-{num(h * 0.8)}m1.6 {num(h * 0.8)}v-{num(h)}m0 {num(h)}l1.6-{num(h * 0.8)}")
                x += rng.uniform(11, 15)
        for _ in range(26):
            x = rng.uniform(20, W - 20)
            y = contour(k, x) + (lip(k, x) - contour(k, x)) * rng.uniform(0.25, 0.85)
            shine.append(f"M{num(x)} {num(y)}h{num(rng.uniform(8, 22))}")
        self.add(
            f'<g clip-path="url(#paddy{k})" fill="none" stroke-linecap="round">'
            f'<g class="shimmer"><path d="{"".join(shine)}" stroke="#ffffff" stroke-width="1.1" opacity=".35"/></g>'
            f'<path d="{"".join(tufts)}" stroke="{mix(rice, "#2c4818", 0.15)}" stroke-width="1.25"/></g>'
        )

    def homestead(self):
        cx = SUMMIT_X
        ground = hilltop(cx) + 2
        self.add(self.bamboo(cx - 74, hilltop(cx - 74) + 3))
        self.add(self.tree(cx + 70, hilltop(cx + 70) + 3, 13, False, 0.6))
        self.add(self.tree(cx + 88, hilltop(cx + 88) + 3, 9, False, 0.2))
        self.stilt_house(cx, ground)

    def bamboo(self, x, ground):
        stalk = self.lit("#5d8a3a")
        leaf = self.lit("#3f6e2f")
        stalks, leaves = [], []
        for i, (dx, h, lean) in enumerate([(-6, 46, -9), (-2, 54, -4), (2, 50, 3), (6, 42, 10), (0, 38, 0)]):
            tip_x, tip_y = x + dx + lean, ground - h
            stalks.append(f"M{num(x + dx)} {num(ground)}Q{num(x + dx)} {num(ground - h * 0.6)} {num(tip_x)} {num(tip_y)}")
            for j in range(4):
                t = 0.45 + j * 0.16
                lx = x + dx + lean * t * t
                ly = ground - h * t
                side = 1 if (i + j) % 2 else -1
                leaves.append(f"M{num(lx)} {num(ly)}q{num(side * 6)} -2 {num(side * 11)} 2q{num(-side * 6)} 0 {num(-side * 11)} -2")
        return (
            f'<path d="{"".join(stalks)}" fill="none" stroke="{stalk}" stroke-width="1.6"/>'
            f'<path d="{"".join(leaves)}" fill="{leaf}"/>'
        )

    def stilt_house(self, cx, ground):
        w = 96
        x0 = cx - w / 2
        floor = ground - 15
        wall_top = floor - 22
        eave = wall_top + 5
        ridge_y = wall_top - 33
        post = self.lit("#3e2a1c")
        beam = self.lit("#5a3b25")
        wood = self.lit("#8b5c37")
        plank = self.lit("#6c4429")
        thatch = self.lit("#b88d4f")
        thatch_dark = self.lit("#8a6534")
        thatch_light = self.lit("#d8b273")
        window = "#ffd889" if self.phase in ("dusk", "night") else self.lit("#2b1b10")
        span = range(int(cx - 58), int(cx + 59), 4)
        shadow = [(x, hilltop(x) + 1) for x in span] + [(x, hilltop(x) + 7) for x in reversed(span)]
        parts = [f'<path d="{shape(shadow)}" fill="#000" opacity=".2"/>']
        for i in range(6):
            px = x0 + 5 + i * (w - 10) / 5
            parts.append(f'<rect x="{num(px - 1.7)}" y="{num(floor)}" width="3.4" height="15" fill="{post}"/>')
        parts.append(
            f'<path d="M{num(x0 + 5)} {num(ground - 2)}L{num(x0 + 24)} {num(floor + 2)}M{num(x0 + 24)} {num(ground - 2)}'
            f'L{num(x0 + 43)} {num(floor + 2)}M{num(x0 + w - 5)} {num(ground - 2)}L{num(x0 + w - 24)} {num(floor + 2)}" '
            f'stroke="{post}" stroke-width="1.4" opacity=".8"/>'
        )
        ladder_x = x0 - 16
        rungs = "".join(
            f"M{num(ladder_x + 3 + t * 13)} {num(ground - t * 15)}h7" for t in (0.2, 0.45, 0.7, 0.92)
        )
        parts.append(
            f'<path d="M{num(ladder_x + 2)} {num(ground)}L{num(ladder_x + 15)} {num(floor)}'
            f'M{num(ladder_x + 9)} {num(ground)}L{num(ladder_x + 22)} {num(floor)}{rungs}" stroke="{beam}" stroke-width="1.6"/>'
        )
        parts.append(f'<rect x="{num(x0 - 7)}" y="{num(floor - 3)}" width="{w + 14}" height="5" fill="{beam}"/>')
        parts.append(f'<rect x="{num(x0 + 3)}" y="{num(wall_top)}" width="{w - 6}" height="22" fill="{wood}"/>')
        planks = "".join(f"M{num(x0 + 3 + i * 5)} {num(wall_top)}v22" for i in range(1, (w - 6) // 5 + 1))
        parts.append(f'<path d="{planks}" stroke="{plank}" stroke-width=".8" opacity=".8"/>')
        parts.append(f'<rect x="{num(cx - 7)}" y="{num(floor - 18)}" width="12" height="18" fill="{self.lit("#3b2616")}"/>')
        for wx in (x0 + 14, x0 + w - 28):
            parts.append(
                f'<rect x="{num(wx)}" y="{num(wall_top + 7)}" width="14" height="10" fill="{window}"/>'
                f'<path d="M{num(wx + 7)} {num(wall_top + 7)}v10M{num(wx)} {num(wall_top + 12)}h14" stroke="{plank}" stroke-width="1"/>'
            )
        roof = [(x0 - 22, eave), (x0 + 16, ridge_y), (x0 + w - 16, ridge_y), (x0 + w + 22, eave)]
        self.defs.append(f'<clipPath id="roof"><path d="{shape(roof)}"/></clipPath>')
        parts.append(f'<path d="{shape(roof)}" fill="{thatch}"/>')
        rows = []
        for j in range(7):
            y = ridge_y + 3 + j * (eave - ridge_y) / 7
            rows.append(
                f'<path d="M{num(x0 - 30)} {num(y)}H{num(x0 + w + 30)}" stroke="{thatch_dark}" stroke-width="3.2" '
                f'stroke-dasharray="1 1.6 1.4 2.2" stroke-dashoffset="{j}"/>'
                f'<path d="M{num(x0 - 30)} {num(y - 2)}H{num(x0 + w + 30)}" stroke="{thatch_light}" stroke-width="1.2" '
                f'stroke-dasharray="1.2 3.4" stroke-dashoffset="{j * 1.3}" opacity=".8"/>'
            )
        parts.append(f'<g clip-path="url(#roof)">{"".join(rows)}</g>')
        parts.append(
            f'<path d="M{num(x0 - 22)} {num(eave)}H{num(x0 + w + 22)}" stroke="{thatch_dark}" stroke-width="3" '
            f'stroke-dasharray="2 1.2 1.5 1"/>'
        )
        parts.append(
            f'<path d="M{num(x0 + 14)} {num(ridge_y)}H{num(x0 + w - 14)}" stroke="{post}" stroke-width="3" stroke-linecap="round"/>'
        )
        horns = ""
        for hx in (x0 + 16, x0 + w - 16):
            horns += (
                f"M{num(hx - 6)} {num(ridge_y + 2)}Q{num(hx)} {num(ridge_y - 3)} {num(hx + 5)} {num(ridge_y - 11)}"
                f"M{num(hx + 6)} {num(ridge_y + 2)}Q{num(hx)} {num(ridge_y - 3)} {num(hx - 5)} {num(ridge_y - 11)}"
            )
        parts.append(f'<path d="{horns}" fill="none" stroke="{post}" stroke-width="1.8" stroke-linecap="round"/>')
        if self.phase in ("dawn", "dusk"):
            sx, sy = x0 + w - 30, ridge_y + 4
            parts.append(
                f'<path class="smoke" d="M{num(sx)} {num(sy)}c-7-9 7-15 1-25s8-15 1-27" fill="none" stroke="#efe9e1" '
                f'stroke-width="5" stroke-linecap="round" opacity=".45"/>'
            )
        self.add(*parts)
        self.window_spots = [(x0 + 21, wall_top + 12), (x0 + w - 21, wall_top + 12)]

    def water(self):
        top, deep = self.p["water"]
        self.defs.append(
            f'<linearGradient id="pond" x1="0" y1="510" x2="0" y2="{H}" gradientUnits="userSpaceOnUse">'
            f'<stop offset="0" stop-color="{top}"/><stop offset="1" stop-color="{deep}"/></linearGradient>'
        )
        edge = [(x, shore(x)) for x in XS]
        self.add(f'<path d="{line(edge)}L{W + 12} {H}L-12 {H}Z" fill="url(#pond)"/>')
        reflection = [(x, shore(x) + 15 + 3 * math.sin(x / 31)) for x in XS]
        bottom_rice = self.lit(ramp(RICE_STOPS, self.months[-1].ripeness))
        self.add(
            f'<path d="{shape(edge + reflection[::-1])}" fill="{mix(bottom_rice, deep, 0.45)}" opacity=".35"/>',
            f'<path d="{line(edge)}" fill="none" stroke="{self.lit("#5a4630")}" stroke-width="3"/>',
            f'<path d="{line([(x, y + 1.5) for x, y in edge])}" fill="none" stroke="{self.lit("#a5845a")}" stroke-width="1" opacity=".7"/>',
        )
        if self.phase == "night":
            cx, color = moon_position(self.moment)[0], "#f3efd9"
        else:
            cx, color = sun_position(self.moment)[0], self.p["sun"]
        streak = "".join(
            f'<path d="M{num(cx - 30 + i * 2.6)} {num(532 + i * 9)}h{num(60 - i * 5.2)}" opacity="{0.6 - i * 0.07:.2f}"/>'
            for i in range(7)
        )
        self.add(
            f'<g stroke="{color}" stroke-width="2.4" stroke-linecap="round" stroke-dasharray="14 5 8 4" class="shimmer">{streak}</g>'
        )
        rng = random.Random(3)
        ripples = ["", ""]
        for i in range(70):
            x = rng.uniform(10, W - 10)
            y = rng.uniform(shore(x) + 10, H - 4)
            ripples[i % 2] += f"M{num(x)} {num(y)}q{num(rng.uniform(5, 12))} -2.2 {num(rng.uniform(12, 28))} 0"
        self.add(
            f'<g class="shimmer"><path d="{ripples[0]}" fill="none" stroke="#fff" stroke-width="1.1" stroke-linecap="round" opacity=".32"/></g>',
            f'<g class="shimmer late"><path d="{ripples[1]}" fill="none" stroke="#fff" stroke-width="1.1" stroke-linecap="round" opacity=".26"/></g>',
        )
        rng = random.Random(9)
        reeds = []
        for start, stop in [(150, 235), (560, 600), (1035, 1205)]:
            x = start
            while x < stop:
                h, lean = rng.uniform(6, 15), rng.uniform(-3, 3)
                reeds.append(f"M{num(x)} {num(shore(x) + 2)}q{num(lean * 0.3)} {num(-h * 0.6)} {num(lean)} {num(-h)}")
                x += rng.uniform(2.5, 6)
        self.add(
            f'<path d="{"".join(reeds)}" fill="none" stroke="{self.lit("#4f7a35")}" stroke-width="1.3" stroke-linecap="round"/>'
        )
        for x, y, rx, angle in [(54, 586, 19, 20), (98, 566, 14, 200), (30, 556, 11, 120), (1150, 584, 18, 330), (1112, 562, 13, 160)]:
            self.add(self.lotus_pad(x, y, rx, angle))
        self.add(self.lotus_flower(78, 577), self.lotus_flower(1134, 570, 0.8))

    def lotus_pad(self, x, y, rx, angle):
        ry = rx * 0.36
        a1, a2 = math.radians(angle - 16), math.radians(angle + 16)
        p1 = (x + rx * math.cos(a1), y + ry * math.sin(a1))
        p2 = (x + rx * math.cos(a2), y + ry * math.sin(a2))
        return (
            f'<ellipse cx="{num(x + 2)}" cy="{num(y + 2)}" rx="{rx}" ry="{num(ry)}" fill="#000" opacity=".15"/>'
            f'<path d="M{num(x)} {num(y)}L{num(p2[0])} {num(p2[1])}A{rx} {num(ry)} 0 1 1 {num(p1[0])} {num(p1[1])}Z" '
            f'fill="{self.lit("#4f8f3f")}" stroke="{self.lit("#2f6a2c")}" stroke-width="1"/>'
        )

    def lotus_flower(self, x, y, s=1.0):
        petal = self.lit("#f4a9bd")
        inner = self.lit("#fbd3de")
        petals = "".join(
            f'<ellipse cx="{num(x + dx * s)}" cy="{num(y - 5 * s)}" rx="{num(3 * s)}" ry="{num(7 * s)}" '
            f'transform="rotate({rot} {num(x + dx * s)} {num(y)})"/>'
            for dx, rot in [(-6, -38), (-3, -16), (3, 16), (6, 38)]
        )
        return (
            f'<g fill="{petal}">{petals}</g>'
            f'<ellipse cx="{num(x)}" cy="{num(y - 6 * s)}" rx="{num(3.4 * s)}" ry="{num(8 * s)}" fill="{inner}"/>'
        )

    def koi_pond(self):
        if not self.koi:
            return
        self.defs.append(f'<path id="koi-body" d="{KOI_BODY}"/>')
        self.defs.append('<clipPath id="koi-clip"><use href="#koi-body"/></clipPath>')
        pellets_each = min(3 + self.fed_today, 8) if self.fed_today else 0
        for i, (repo, x, y, length, facing) in enumerate(self.koi_spots()):
            if pellets_each:
                food = random.Random(f"{repo['name']} food")
                self.add(self.pellets(x + facing * length * 0.62, y - 2, pellets_each, food))
            markings = random.Random(repo["name"])
            self.add(self.koi_fish(x, y, length, facing, KOI_ORDER[i % len(KOI_ORDER)], markings, i))

    def koi_spots(self):
        n = len(self.koi)
        for i, repo in enumerate(self.koi):
            length = max(48, min(100, 36 + 8 * math.sqrt(repo["stars"])))
            x = 170 + (i + 0.5) * (860 / n)
            y = 567 if i % 2 == 0 else 580
            yield repo, x, y, length, 1 if i % 2 == 0 else -1

    def koi_fish(self, x, y, length, facing, variety, rng, index):
        base, patches = koi_markings(variety, rng)
        fin = mix(base, "#ffffff", 0.45)
        marks = "".join(
            f'<ellipse cx="{cx:.3f}" cy="{cy:.3f}" rx="{rx:.3f}" ry="{ry:.3f}" fill="{self.lit(color)}"/>'
            for color, cx, cy, rx, ry in patches
        )
        return (
            f'<g transform="translate({num(x)} {num(y)})"><g class="swim" style="animation-delay:-{index * 3.7:.1f}s">'
            f'<g transform="scale({num(facing * length)} {num(length)})">'
            f'<use href="#koi-body" transform="translate(.05 .1)" fill="#08202a" opacity=".3"/>'
            f'<path d="{KOI_TAIL}" fill="{self.lit(fin)}" opacity=".75"/>'
            f'<ellipse cx=".22" cy="-.15" rx=".09" ry=".04" transform="rotate(-35 .22 -.15)" fill="{self.lit(fin)}" opacity=".7"/>'
            f'<ellipse cx=".22" cy=".15" rx=".09" ry=".04" transform="rotate(35 .22 .15)" fill="{self.lit(fin)}" opacity=".7"/>'
            f'<use href="#koi-body" fill="{self.lit(base)}"/>'
            f'<g clip-path="url(#koi-clip)">{marks}'
            f'<ellipse cx=".08" cy="-.03" rx=".3" ry=".045" fill="#fff" opacity=".2"/></g>'
            f'<path d="M.16 0H-.24" stroke="#000" stroke-width=".018" opacity=".09"/>'
            f'<circle cx=".43" cy="-.055" r=".014" fill="#1b1b1b"/><circle cx=".43" cy=".055" r=".014" fill="#1b1b1b"/>'
            f"</g></g></g>"
        )

    def pellets(self, x, y, count, rng):
        parts = []
        for _ in range(count):
            px, py = x + rng.uniform(-16, 16), y + rng.uniform(-11, 11)
            parts.append(
                f'<circle cx="{num(px)}" cy="{num(py)}" r="2.7" fill="{self.lit("#b5702f")}"/>'
                f'<circle cx="{num(px - 0.7)}" cy="{num(py - 0.8)}" r="1" fill="#f3cf8e"/>'
            )
        rings = "".join(
            f'<ellipse class="ring" style="animation-delay:-{j * 1.1:.1f}s" cx="{num(x + rng.uniform(-8, 8))}" '
            f'cy="{num(y + rng.uniform(-5, 5))}" rx="{num(10 + 4 * j)}" ry="{num(3.4 + 1.3 * j)}"/>'
            for j in range(3)
        )
        return f'<g fill="none" stroke="#fff" stroke-width="1.1" opacity=".6">{rings}</g>' + "".join(parts)

    def farmers(self):
        for i, user in enumerate(self.planters):
            band, x = FARMER_SLOTS[i]
            y = contour(band, x) + (lip(band, x) - contour(band, x)) * 0.8
            scale = 0.95 + 0.28 * band / (MONTHS - 1)
            rng = random.Random(user.lower())
            rice = self.lit(ramp(RICE_STOPS, self.months[band].ripeness))
            self.add(self.farmer(x, y, scale, rng, mix(rice, "#2c4818", 0.3)))
            self.farmer_tags.append((x, y - 31 * scale - 5, user))

    def farmer(self, x, y, s, rng, tuft):
        shirt = self.lit(rng.choice(SHIRTS))
        sash = self.lit(rng.choice(SASHES))
        trousers = self.lit("#25232c")
        skin = self.lit("#c68c5a")
        hat = self.lit("#f2e2b1")
        hat_shade = self.lit("#cdb57a")
        bend = rng.choice([0, 14, 22])
        facing = rng.choice([1, -1])
        seedling = self.lit("#5fa03a")
        return (
            f'<g transform="translate({num(x)} {num(y)}) scale({num(facing * s)} {num(s)})">'
            f'<ellipse cx="0" cy="0" rx="9" ry="2.2" fill="none" stroke="#fff" stroke-width=".9" opacity=".45"/>'
            f'<path d="M-3.5-1L-3.2-9H3.2L3.5-1H1.1L.1-5.6-.9-1Z" fill="{trousers}"/>'
            f'<g transform="rotate({bend} 0 -9)">'
            f'<path d="M-4.2-9L-4.8-18.5Q0-20.5 4.8-18.5L4.2-9Z" fill="{shirt}"/>'
            f'<rect x="-4.4" y="-11.2" width="8.8" height="2.2" fill="{sash}"/>'
            f'<path d="M3.6-17L7-9.5M-3.6-17L-5.6-10.5" stroke="{shirt}" stroke-width="2.3" stroke-linecap="round"/>'
            f'<path d="M7.2-9.2l-1.3-4.4M7.6-9.2v-4.8M8-9.2l1.3-4.4" stroke="{seedling}" stroke-width=".9" stroke-linecap="round"/>'
            f'<circle cx="0" cy="-21" r="2.9" fill="{skin}"/>'
            f'<path d="M-10-20.3L0-29.6L10-20.3Q0-18.4-10-20.3Z" fill="{hat}"/>'
            f'<path d="M0-29.6L10-20.3Q5-19.1 0-18.9Z" fill="{hat_shade}"/>'
            f'<path d="M-6.6-23.4Q0-22.4 6.6-23.4M-3.4-26.5Q0-26 3.4-26.5" fill="none" stroke="{hat_shade}" stroke-width=".7"/>'
            f'<path d="M-10-20.3Q0-18.4 10-20.3" fill="none" stroke="{self.lit("#a88a4e")}" stroke-width=".8"/>'
            f"</g>"
            f'<path d="M-6 .5l-1.2-4.2M-5.4 .5v-4.6M-4.8 .5l1.2-4.2M3.8 .8l-1-3.8M4.4 .8v-4.2M5 .8l1-3.8" '
            f'stroke="{tuft}" stroke-width="1" stroke-linecap="round"/>'
            f"</g>"
        )

    def lamplight(self):
        for x, y in self.window_spots:
            self.add(self.halo(x, y, 46, "#ffc65e", 0.55))
        if self.phase == "night":
            rng = random.Random(5)
            flies = []
            for _ in range(16):
                band = rng.randint(3, MONTHS - 1)
                x = rng.uniform(80, W - 40)
                y = contour(band, x) - rng.uniform(4, 14)
                flies.append(f'<circle cx="{num(x)}" cy="{num(y)}" r="1.5"/><circle cx="{num(x)}" cy="{num(y)}" r="4" opacity=".25"/>')
            self.add(f'<g fill="#eef89a" class="twinkle">{"".join(flies)}</g>')

    def labels(self):
        parts = []
        for k, month in enumerate(self.months):
            y = (contour(k, 34) + lip(k, 34)) / 2 + 5.5
            name = month_abbr[month.start.month]
            if k == 0 or month.start.month == 1:
                name += f" {month.start.year}"
            parts.append(
                f'<text x="16" y="{num(y)}" class="halo"><tspan class="month">{name}</tspan>'
                f'<tspan class="count" dx="5">{month.total:,}</tspan></text>'
            )
        for repo, x, y, length, _ in self.koi_spots():
            parts.append(
                f'<text x="{num(x)}" y="{num(y - length * 0.15 - 8)}" text-anchor="middle" class="koi-name halo">'
                f'{esc(repo["name"])}</text>'
            )
        for x, y, user in self.farmer_tags:
            shown = user if len(user) <= 16 else user[:15] + "..."
            parts.append(f'<text x="{num(x)}" y="{num(y)}" text-anchor="middle" class="tag halo">@{esc(shown)}</text>')
        clock = self.moment.strftime("%H:%M")
        parts.append('<text x="30" y="46" class="title soft">Ruộng Commit</text>')
        parts.append(
            f'<text x="31" y="68" class="subtitle soft">Mù Cang Chải at {clock} Hanoi time, '
            f"{self.last_year:,} contributions in the last year</text>"
        )
        self.defs.append(
            '<linearGradient id="ripen" x1="0" x2="1">'
            + "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in RICE_STOPS)
            + "</linearGradient>"
        )
        parts.append(
            f'<text x="{W - 30}" y="40" text-anchor="end" class="legend soft">Each terrace is one month</text>'
            f'<rect x="{W - 170}" y="49" width="140" height="7" rx="3.5" fill="url(#ripen)" stroke="#fff" stroke-opacity=".6"/>'
            f'<text x="{W - 170}" y="72" class="legend soft">fewer</text>'
            f'<text x="{W - 30}" y="72" text-anchor="end" class="legend soft">more commits</text>'
        )
        self.add(*parts)


def koi_markings(variety, rng):
    red, black, white = "#e2552c", "#25242a", "#f8f4ec"

    def blobs(count, color, low, high):
        return [
            (color, rng.uniform(-0.22, 0.4), rng.uniform(-0.1, 0.1), rng.uniform(low, high), rng.uniform(low, high) * 0.8)
            for _ in range(count)
        ]

    if variety == "kohaku":
        return white, blobs(4, red, 0.08, 0.13)
    if variety == "showa":
        return "#2a2930", blobs(3, "#ec6b2d", 0.09, 0.13) + blobs(2, white, 0.05, 0.08)
    if variety == "ogon":
        return "#f0a23a", [("#ffd585", 0.12, -0.02, 0.3, 0.05)]
    if variety == "sanke":
        return white, blobs(3, red, 0.08, 0.12) + blobs(4, black, 0.025, 0.045)
    if variety == "tancho":
        return white, [(red, 0.36, 0, 0.07, 0.065)]
    if variety == "bekko":
        return "#ee7d33", blobs(5, black, 0.03, 0.05)
    return white, blobs(4, black, 0.07, 0.12)


@dataclass
class Month:
    start: date
    total: int
    ripeness: float


def build_months(days, moment):
    starts = month_starts(moment)
    totals = [sum(count for day, count in days.items() if day.startswith(start.strftime("%Y-%m"))) for start in starts]
    most = max(max(totals), 1)
    return [Month(start, total, total / most) for start, total in zip(starts, totals)]


def issue_link(title, body):
    return f"{REPO_URL}/issues/new?title={quote(title)}&amp;body={quote(body)}"


def join_names(names):
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


def readme_block(scene, planters):
    ripest = max(scene.months, key=lambda month: month.total)
    current = scene.months[-1]
    current_name = month_name[current.start.month]
    if ripest is current and current.total > 0:
        growth = f"{current_name} is already the ripest even though it is still growing"
    else:
        stage = "was just planted" if scene.moment.day <= 7 else "is still growing"
        growth = f"{month_name[ripest.start.month]} is the ripest and {current_name} {stage}"

    koi = scene.koi
    if not koi:
        koi_text = "No repo has 10 stars yet, so the paddy is still waiting for its first koi."
    else:
        named = []
        for i, repo in enumerate(koi):
            stars = f"{repo['stars']} stars" if i == 0 else repo["stars"]
            named.append(f'<a href="{esc(repo["url"])}">{esc(repo["name"])}</a> ({stars})')
        if len(koi) == 1:
            koi_text = f"One koi swims in the paddy, for my one repo with at least 10 stars: {named[0]}."
        else:
            koi_text = (
                f"{count_words(len(koi)).capitalize()} koi swim in the paddy, one for each repo with at least "
                f"10 stars: {join_names(named)}."
            )

    if not planters:
        visitor_text = (
            "No one has planted a seedling in the last 30 days, so the terraces are waiting for their first farmer."
        )
    else:
        links = [f'<a href="https://github.com/{esc(user)}">@{esc(user)}</a>' for user in planters]
        shown = links if len(links) <= 3 else links[:2] + [f"{len(links) - 2} others"]
        count = len(planters)
        noun = "visitor planted a seedling" if count == 1 else "visitors planted seedlings"
        visitor_text = f"{count_words(count).capitalize()} {noun} in the last 30 days ({join_names(shown)})."

    fed = scene.fed_today
    if fed == 0:
        feed_text = "Nobody has fed the koi yet today, so they are circling hopefully."
    elif fed == 1:
        feed_text = "The koi have been fed once today."
    else:
        feed_text = f"The koi have been fed {fed} times today."

    caption = (
        f"Ruộng Commit: rice terraces in the hills of Mù Cang Chải that grow with my GitHub activity, "
        f"{scene.last_year:,} contributions in the last year. Each terrace is a month, and the rice ripens from "
        f"green to gold as the commits come in, so {growth}. {koi_text} {visitor_text} {feed_text} "
        f"The sky follows the time in Hanoi, where it's {PHASE_WORDS[scene.phase]} right now."
    )
    rule = "Each visitor gets one farm chore a day, Hanoi time."
    plant = issue_link(
        "terrace: plant",
        f"Just hit **Create**. A farmer in a nón lá will join the terraces on github.com/{LOGIN} "
        f"in about a minute.\n\n{rule}",
    )
    feed = issue_link(
        "terrace: feed",
        f"Just hit **Create**. A handful of food will land in the koi paddy on github.com/{LOGIN} "
        f"in about a minute.\n\n{rule}",
    )
    return f"""<p align="center"><img src="terrace/terrace.svg" width="100%" alt="{esc(scene.alt_text())}"/></p>

<p align="center"><sub>{caption}</sub></p>

<p align="center">
  <a href="{plant}"><img src="https://img.shields.io/badge/Plant_a_seedling-3f7d4f?style=for-the-badge" alt="Plant a seedling"/></a>
  <a href="{feed}"><img src="https://img.shields.io/badge/Feed_the_koi-d9822b?style=for-the-badge" alt="Feed the koi"/></a>
  <br/>
  <sub>Buttons open a pre-filled issue. Hit Create and the farm updates in about a minute.</sub>
</p>

<details>
<summary>How Ruộng Commit works</summary>
<br>
<p>Everything on this hill comes from my public GitHub activity, read from GitHub's GraphQL API: the contribution calendar and my public, non-fork repos.</p>
<p>Each of the 12 terraces is a calendar month, the oldest at the top and the current month at the bottom by the water. A terrace's rice ripens from green to gold by how many contributions that month had compared to my busiest month of the last year. The current month counts its running total, so it starts out as seedlings in a flooded paddy and ripens as the month fills in.</p>
<p>Each koi is one of my public repos with at least 10 stars, and the more stars, the bigger the koi. Every farmer in a nón lá is a visitor who planted a seedling in the last 30 days, and floating food means someone fed the koi today. Each visitor gets one chore a day, Hanoi time.</p>
<p>The sky follows the time in Hanoi, with the sun and the real phase of the moon moving through the hours and a lamp lit in the stilt house after dark. A GitHub Action redraws the farm a few times a day and whenever someone opens a plant or feed issue, so there's no server. Every visit is kept in <a href="terrace/state.json">terrace/state.json</a>.</p>
</details>"""


def update_readme(block):
    import sys

    sys.path.insert(0, str(HERE.parent))
    from profile.rotate import publish

    publish("terrace", block)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--phase", choices=list(PHASE_TIMES), help="preview a sky phase at its scheduled Hanoi time today")
    parser.add_argument("--at", help="ISO datetime to draw, read as Hanoi time when it has no offset")
    parser.add_argument("--out", type=Path, default=SVG_PATH, help="where to write the SVG")
    parser.add_argument("--state", type=Path, default=STATE_PATH, help="visitor state JSON")
    parser.add_argument("--data", type=Path, help="read GitHub data from this JSON file instead of the API")
    parser.add_argument("--save-data", type=Path, help="also write the fetched GitHub data to this JSON file")
    parser.add_argument("--no-readme", action="store_true", help="leave README.md untouched")
    return parser.parse_args()


def main():
    args = parse_args()
    moment = datetime.now(HANOI).replace(second=0, microsecond=0)
    if args.at:
        moment = datetime.fromisoformat(args.at)
        moment = moment.replace(tzinfo=HANOI) if moment.tzinfo is None else moment.astimezone(HANOI)
    if args.phase:
        hour, minute = PHASE_TIMES[args.phase]
        moment = moment.replace(hour=hour, minute=minute)

    data = json.loads(args.data.read_text()) if args.data else fetch_github(moment)
    if args.save_data:
        args.save_data.write_text(json.dumps(data, indent=2) + "\n")

    state = load_state(args.state)
    planters = recent_planters(state, moment)
    koi = [repo for repo in data["repos"] if repo["stars"] >= MIN_KOI_STARS]
    koi = sorted(koi, key=lambda repo: (-repo["stars"], repo["name"].lower()))[:MAX_KOI]
    scene = Scene(
        phase=phase_at(moment),
        moment=moment,
        months=build_months(data["days"], moment),
        koi=koi,
        planters=planters,
        fed_today=feedings_on(state, moment.date()),
        last_year=data["last_year"],
    )
    svg = scene.render()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if not args.out.exists() or args.out.read_text() != svg:
        args.out.write_text(svg)
    if not args.no_readme:
        update_readme(readme_block(scene, planters))
    print(f"Drew {args.out} for {moment:%Y-%m-%d %H:%M} Hanoi ({scene.phase}), {len(svg) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
