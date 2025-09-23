#!/usr/bin/env python3
"""
Generate a GitHub-like contribution calendar from WakaTime daily totals.

- Reads WAKATIME_API_KEY from env
- Pulls last 365 days from WakaTime summaries API
- Writes SVG to images/wakatime_calendar_dark.svg and images/wakatime_calendar_light.svg
"""

import os, sys, datetime as dt, requests
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np

API = "https://wakatime.com/api/v1/users/current/summaries"

def get_days(start: dt.date, end: dt.date, api_key: str):
    r = requests.get(
        API,
        params={"start": start.isoformat(), "end": end.isoformat()},
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json().get("data", [])
    # Map yyyy-mm-dd -> total_seconds
    out = {}
    for d in data:
        date = d["range"]["date"]
        out[date] = d["grand_total"]["total_seconds"]
    return out

def make_matrix(day_map, end_date):
    # Build 7 x 53 grid aligned to weeks ending on end_date (like GitHub)
    start_date = end_date - dt.timedelta(days=364)
    # pad to start on Sunday
    # GitHub calendar columns are weeks (Sun..Sat). Find the Sunday on/after start_date.
    start_week_sun = start_date - dt.timedelta(days=(start_date.weekday()+1) % 7)
    # Build all dates shown
    dates = [start_week_sun + dt.timedelta(days=i) for i in range(7*53)]
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
        bg = "#0d1117"; edge = "#30363d"; txt = "#e6edf3"
        cmap = mpl.cm.Blues
    else:
        bg = "#ffffff"; edge = "#d0d7de"; txt = "#24292f"
        cmap = mpl.cm.Blues
    ax.set_facecolor(bg)
    plt.gcf().set_facecolor(bg)

    # Color scaling: 0h → light, 6h+ → max
    norm = mpl.colors.Normalize(vmin=0, vmax=6)
    for r in range(mat.shape[0]):
        for c in range(mat.shape[1]):
            v = mat[r, c]
            color = cmap(norm(v)) if v > 0 else (0, 0, 0, 0)  # transparent for 0
            rect = mpl.patches.Rectangle((c, 6 - r), 0.9, 0.9, linewidth=0.6,
                                         edgecolor=edge, facecolor=color)
            ax.add_patch(rect)

    ax.set_xlim(-0.5, mat.shape[1] + 0.5)
    ax.set_ylim(-0.5, 6.5)
    ax.axis("off")

    # Legend
    legend_vals = [0, 1, 2, 4, 6]
    legend = []
    for v in legend_vals:
        legend.append(mpl.patches.Patch(facecolor=cmap(norm(v)), edgecolor=edge))
    ax.legend(legend, [f"{v}h" for v in legend_vals], frameon=False, labelcolor=txt,
              loc="lower right", bbox_to_anchor=(1.0, -0.2), ncol=len(legend_vals))
    plt.tight_layout(pad=0.4)
    plt.savefig(out, format="svg", bbox_inches="tight")
    plt.close()

def main():
    api_key = os.getenv("WAKATIME_API_KEY")
    if not api_key:
        print("WAKATIME_API_KEY env var not set", file=sys.stderr); sys.exit(1)

    end = dt.date.today()
    start = end - dt.timedelta(days=364)
    day_map = get_days(start, end, api_key)
    mat, _ = make_matrix(day_map, end)

    draw_calendar(mat, theme="dark", out="images/wakatime_calendar_dark.svg")
    draw_calendar(mat, theme="light", out="images/wakatime_calendar_light.svg")

if __name__ == "__main__":
    main()
