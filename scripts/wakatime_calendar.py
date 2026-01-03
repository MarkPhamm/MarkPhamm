#!/usr/bin/env python3
"""
Generate a GitHub-like contribution calendar from WakaTime daily totals.

- Reads WAKATIME_API_KEY from env
- Pulls last 365 days from WakaTime heartbeats API (free account compatible)
- Aggregates heartbeats by day to calculate daily coding time
- Uses Basic authentication for personal API keys
- Writes SVG to images/wakatime_calendar_dark.svg and images/wakatime_calendar_light.svg
- Downloads WakaTime share charts (Languages, Categories, Activity) locally
"""

import os, sys, datetime as dt, requests, time
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
from dotenv import load_dotenv
import base64

API = "https://api.wakatime.com/api/v1/users/current/heartbeats"

# WakaTime share chart URLs - these are public embeddable charts
WAKATIME_SHARE_CHARTS = {
    "wakatime_activity": "https://wakatime.com/share/@MarkPham/bf84f45c-1df0-48c0-95b2-241fa9218b90.svg",
    "wakatime_languages": "https://wakatime.com/share/@MarkPham/09c08320-7dd3-4d9c-a627-d1b4d27d6d2f.svg",
    "wakatime_categories": "https://wakatime.com/share/@MarkPham/585625a7-3a6e-4abc-9a4f-0961c335b118.svg",
}


def download_share_charts():
    """Download WakaTime share charts locally so they render on GitHub."""
    Path("images").mkdir(parents=True, exist_ok=True)

    for name, url in WAKATIME_SHARE_CHARTS.items():
        print(f"Downloading {name} from {url}...")
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()

            out_path = f"images/{name}.svg"
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(r.text)
            print(f"  Saved to {out_path}")
        except requests.exceptions.RequestException as e:
            print(f"  Error downloading {name}: {e}")


def get_days(start: dt.date, end: dt.date, api_key: str):
    # Use Basic authentication for WakaTime personal API keys
    auth_string = base64.b64encode(f"{api_key}:".encode()).decode()

    # Aggregate heartbeats by day
    day_totals = {}
    current_date = start
    request_count = 0

    total_days = (end - start).days + 1

    while current_date <= end:
        date_str = current_date.isoformat()
        days_processed = (current_date - start).days + 1
        print(f"Fetching data for {date_str}... ({days_processed}/{total_days})")

        try:
            r = requests.get(
                API,
                params={"date": date_str},
                headers={"Authorization": f"Basic {auth_string}"},
                timeout=30,
            )
            r.raise_for_status()
            request_count += 1

            data = r.json().get("data", [])

            # Calculate total seconds for this day
            if data:
                # Group heartbeats by time intervals and calculate durations
                total_seconds = 0
                prev_time = None

                for heartbeat in data:
                    current_time = heartbeat["time"]

                    if prev_time is not None:
                        # If gap is less than 2 minutes, count it as active coding time
                        gap = current_time - prev_time
                        if gap <= 120:  # 2 minutes
                            total_seconds += gap

                    prev_time = current_time

                day_totals[date_str] = total_seconds
            else:
                day_totals[date_str] = 0

            # Rate limiting: WakaTime allows ~10 requests per second
            # Let's be conservative with 1 request per 0.2 seconds (5 per second)
            if request_count % 10 == 0:
                print(f"  Rate limiting... (processed {request_count} requests)")
                time.sleep(2)
            else:
                time.sleep(0.2)

        except requests.exceptions.RequestException as e:
            print(f"  Error fetching data for {date_str}: {e}")
            day_totals[date_str] = 0
            time.sleep(1)  # Wait longer on errors

        current_date += dt.timedelta(days=1)

    print(f"Completed! Processed {request_count} requests for {len(day_totals)} days.")
    return day_totals


def make_matrix(day_map, end_date):
    # Build 7 x 53 grid aligned to weeks ending on end_date (like GitHub)
    start_date = end_date - dt.timedelta(days=364)
    # pad to start on Sunday
    # GitHub calendar columns are weeks (Sun..Sat). Find the Sunday on/after start_date.
    start_week_sun = start_date - dt.timedelta(days=(start_date.weekday() + 1) % 7)
    # Build all dates shown
    dates = [start_week_sun + dt.timedelta(days=i) for i in range(7 * 53)]
    # Truncate to end_date’s week
    dates = [d for d in dates if d <= end_date]
    # Fill matrix (rows: Sun..Sat)
    mat = np.zeros((7, 53), dtype=float)
    # Normalize by hours for nicer legend
    for idx, d in enumerate(dates):
        col = idx // 7
        row = d.weekday() + 1  # Monday=1..Sunday=0
        row = 0 if row == 7 else row  # Sunday=0
        val = day_map.get(d.isoformat(), 0.0) / 3600.0  # hours
        if col < 53:
            mat[row, col] = val
    return mat, dates


def draw_calendar(mat, theme="dark", out="images/wakatime_calendar_dark.svg"):
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(12, 2.6), dpi=220)
    ax = plt.gca()
    ax.set_aspect("equal")
    # Theme
    if theme == "dark":
        bg = "#0d1117"
        edge = "#30363d"
        txt = "#e6edf3"
        cmap = mpl.cm.Blues
    else:
        bg = "#ffffff"
        edge = "#d0d7de"
        txt = "#24292f"
        cmap = mpl.cm.Blues
    ax.set_facecolor(bg)
    plt.gcf().set_facecolor(bg)

    # Color scaling: 0h → light, 6h+ → max
    norm = mpl.colors.Normalize(vmin=0, vmax=6)
    for r in range(mat.shape[0]):
        for c in range(mat.shape[1]):
            v = mat[r, c]
            color = cmap(norm(v)) if v > 0 else (0, 0, 0, 0)  # transparent for 0
            rect = mpl.patches.Rectangle(
                (c, 6 - r), 0.9, 0.9, linewidth=0.6, edgecolor=edge, facecolor=color
            )
            ax.add_patch(rect)

    ax.set_xlim(-0.5, mat.shape[1] + 0.5)
    ax.set_ylim(-0.5, 6.5)
    ax.axis("off")

    # Legend
    legend_vals = [0, 1, 2, 4, 6]
    legend = []
    for v in legend_vals:
        legend.append(mpl.patches.Patch(facecolor=cmap(norm(v)), edgecolor=edge))
    ax.legend(
        legend,
        [f"{v}h" for v in legend_vals],
        frameon=False,
        labelcolor=txt,
        loc="lower right",
        bbox_to_anchor=(1.0, -0.2),
        ncol=len(legend_vals),
    )
    plt.tight_layout(pad=0.4)
    plt.savefig(out, format="svg", bbox_inches="tight")
    plt.close()


def main():
    load_dotenv()  # Load environment variables from .env file
    api_key = os.getenv("WAKATIME_API_KEY")
    if not api_key:
        print("WAKATIME_API_KEY env var not set", file=sys.stderr)
        sys.exit(1)

    # Download WakaTime share charts (public, no API key needed)
    print("Downloading WakaTime share charts...")
    download_share_charts()
    print()

    end = dt.date.today()
    start = end - dt.timedelta(days=364)  # Full year (365 days)
    print(f"Fetching WakaTime data from {start} to {end} (365 days)...")
    print("This will take a few minutes due to rate limiting...")
    day_map = get_days(start, end, api_key)
    mat, _ = make_matrix(day_map, end)

    draw_calendar(mat, theme="dark", out="images/wakatime_calendar_dark.svg")
    draw_calendar(mat, theme="light", out="images/wakatime_calendar_light.svg")


if __name__ == "__main__":
    main()
