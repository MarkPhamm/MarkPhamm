"""Pull my GitHub and WakaTime activity into raw/*.json for the dbt sources."""

import base64
import json
import os
import re
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
README = HERE.parent / "README.md"
LOGIN = "MarkPhamm"

GRAPHQL_URL = "https://api.github.com/graphql"
WAKATIME_URL = "https://wakatime.com/api/v1/users/current/summaries"

QUERY = """
query($login: String!, $calendarFrom: DateTime!, $yearFrom: DateTime!, $to: DateTime!) {
  user(login: $login) {
    calendar: contributionsCollection(from: $calendarFrom, to: $to) {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
    thisYear: contributionsCollection(from: $yearFrom, to: $to) {
      commitContributionsByRepository(maxRepositories: 25) {
        repository { name isPrivate }
        contributions { totalCount }
      }
    }
    repositories(
      first: 100
      ownerAffiliations: OWNER
      isFork: false
      privacy: PUBLIC
      orderBy: {field: STARGAZERS, direction: DESC}
    ) {
      nodes {
        name
        stargazerCount
        primaryLanguage { name }
        pushedAt
        createdAt
        description
        url
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


def fetch_github() -> dict:
    now = datetime.now(UTC).replace(microsecond=0)
    variables = {
        "login": LOGIN,
        "calendarFrom": (now - timedelta(days=365)).isoformat(),
        "yearFrom": now.replace(month=1, day=1, hour=0, minute=0, second=0).isoformat(),
        "to": now.isoformat(),
    }
    response = requests.post(
        GRAPHQL_URL,
        json={"query": QUERY, "variables": variables},
        headers={"Authorization": f"Bearer {github_token()}"},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        raise RuntimeError(f"GitHub GraphQL errors: {payload['errors']}")
    return payload["data"]["user"]


def contributions_rows(user: dict) -> list[dict]:
    weeks = user["calendar"]["contributionCalendar"]["weeks"]
    return [
        {"day": day["date"], "contributions": day["contributionCount"]}
        for week in weeks
        for day in week["contributionDays"]
    ]


def repo_rows(user: dict) -> list[dict]:
    return [
        {
            "name": repo["name"],
            "stars": repo["stargazerCount"],
            "language": (repo["primaryLanguage"] or {}).get("name"),
            "pushed_at": repo["pushedAt"],
            "created_at": repo["createdAt"],
            "description": repo["description"],
            "url": repo["url"],
        }
        for repo in user["repositories"]["nodes"]
    ]


def repo_commit_rows(user: dict) -> list[dict]:
    return [
        {"repo": item["repository"]["name"], "commits": item["contributions"]["totalCount"]}
        for item in user["thisYear"]["commitContributionsByRepository"]
        if not item["repository"]["isPrivate"]
    ]


def wakatime_api_rows(api_key: str) -> list[dict]:
    token = base64.b64encode(f"{api_key}:".encode()).decode()
    response = requests.get(
        WAKATIME_URL,
        params={"range": "last_7_days"},
        headers={"Authorization": f"Basic {token}"},
        timeout=30,
    )
    response.raise_for_status()
    return [
        {"day": summary["range"]["date"], "language": language["name"], "seconds": language["total_seconds"]}
        for summary in response.json()["data"]
        for language in summary["languages"]
        if language["total_seconds"] > 0
    ]


def parse_duration(text: str) -> int:
    units = {"hr": 3600, "min": 60, "sec": 1}
    return sum(int(amount) * units[unit] for amount, unit in re.findall(r"(\d+) (hr|min|sec)", text))


def wakatime_readme_rows() -> list[dict]:
    """Weekly totals from the waka-readme block, which only lists the top languages."""
    block = re.search(
        r"<!--START_SECTION:waka-->(.*?)<!--END_SECTION:waka-->",
        README.read_text(encoding="utf-8"),
        re.S,
    )
    if not block:
        return []

    rows = []
    shares = []
    for line in block.group(1).splitlines():
        parts = re.split(r"\s{2,}", line.strip())
        if len(parts) < 3 or not parts[-1].endswith("%"):
            continue
        seconds = parse_duration(parts[1])
        share = float(parts[-1].rstrip("% "))
        if seconds > 0:
            rows.append({"day": None, "language": parts[0], "seconds": seconds})
            shares.append(share)

    if rows and shares[0] > 0:
        week_seconds = rows[0]["seconds"] / (shares[0] / 100)
        other = round(week_seconds - sum(row["seconds"] for row in rows))
        if other >= 60:
            rows.append({"day": None, "language": "Other", "seconds": other})
    return rows


def wakatime_rows() -> list[dict]:
    api_key = os.environ.get("WAKATIME_API_KEY")
    if api_key:
        try:
            rows = wakatime_api_rows(api_key)
            print(f"wakatime: API summaries for the last 7 days, {len(rows)} rows")
            return rows
        except requests.RequestException as error:
            print(f"wakatime: API request failed ({error}), falling back to the README")
    rows = wakatime_readme_rows()
    print(f"wakatime: weekly totals from the waka block in README.md, {len(rows)} rows")
    return rows


def write(name: str, rows: list[dict]) -> None:
    path = RAW / f"{name}.json"
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {path.relative_to(HERE)}: {len(rows)} rows")


def main() -> None:
    RAW.mkdir(exist_ok=True)
    user = fetch_github()
    total = user["calendar"]["contributionCalendar"]["totalContributions"]
    print(f"github: {total} contributions in the last year")
    write("github_contributions", contributions_rows(user))
    write("github_repos", repo_rows(user))
    write("github_repo_commits", repo_commit_rows(user))
    write("wakatime_languages", wakatime_rows())


if __name__ == "__main__":
    main()
