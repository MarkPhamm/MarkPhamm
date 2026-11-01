"""Answer a "query:" issue by running one SELECT against the exported marts."""

import json
import os
import re
import threading
import unicodedata
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb

HERE = Path(__file__).resolve().parent
EXPORTS = HERE / "exports"
STATE = HERE / "state"
LAST_QUERY = STATE / "last_query.json"
QUERY_LOG = STATE / "query_log.json"

OWNER = "MarkPhamm"
REPO_URL = "https://github.com/MarkPhamm/MarkPhamm"
TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")
LOGIN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})")

MAX_SQL_CHARS = 2000
MAX_ROWS = 20
MAX_COLUMNS = 12
MAX_CELL_WIDTH = 40
TIMEOUT_SECONDS = 5
ALLOWED_FIRST_WORDS = {"select", "with", "from", "values", "table", "describe", "summarize", "show"}

EXAMPLE_SQL = """select repo_name, stars, commits_this_year, status
from dim_repos
order by stars desc
limit 5;"""


class QueryError(Exception):
    pass


def extract_sql(body: str) -> str:
    lines = (body or "").replace("\r\n", "\n").split("\n")
    opening = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if opening is None:
            fence = re.fullmatch(r"(`{3,})\s*([\w+-]*)\s*", stripped)
            if fence:
                opening = (index, fence.group(1), fence.group(2).lower())
        elif stripped.startswith(opening[1]) and not stripped.strip("`"):
            if opening[2] in ("", "sql"):
                return "\n".join(lines[opening[0] + 1 : index]).strip()
            opening = None
    if opening and opening[2] in ("", "sql"):
        return "\n".join(lines[opening[0] + 1 :]).strip()
    return (body or "").strip()


def first_word(sql: str) -> str:
    rest = sql
    while True:
        trimmed = re.sub(r"\A(?:\s+|\(|--[^\n]*|/\*.*?\*/)", "", rest, flags=re.S)
        if trimmed == rest:
            break
        rest = trimmed
    match = re.match(r"[A-Za-z_]+", rest)
    return match.group(0).lower() if match else ""


def first_line(error: Exception) -> str:
    lines = str(error).strip().splitlines()
    return (lines[0] if lines else type(error).__name__)[:300]


def open_warehouse() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(":memory:")
    for path in sorted(EXPORTS.glob("*.csv")):
        location = str(path).replace("'", "''")
        con.execute(f"create table \"{path.stem}\" as select * from read_csv_auto('{location}')")
    con.execute("set memory_limit = '512MB'")
    con.execute("set threads = 2")
    con.execute("set enable_external_access = false")
    con.execute("set lock_configuration = true")
    return con


def validate(con: duckdb.DuckDBPyConnection, sql: str) -> str:
    if not sql:
        raise QueryError("I could not find any SQL; put one SELECT inside a ```sql block.")
    if len(sql) > MAX_SQL_CHARS:
        raise QueryError(f"The query is longer than {MAX_SQL_CHARS} characters.")
    try:
        statements = con.extract_statements(sql)
    except duckdb.Error as error:
        raise QueryError(f"DuckDB could not parse it: {first_line(error)}") from None
    if len(statements) != 1 or statements[0].type != duckdb.StatementType.SELECT:
        raise QueryError("Only a single SELECT statement is allowed.")
    if first_word(sql) not in ALLOWED_FIRST_WORDS:
        raise QueryError("Only a single SELECT statement is allowed.")
    return statements[0].query


def run_select(con: duckdb.DuckDBPyConnection, sql: str) -> str:
    statement = validate(con, sql)
    outcome = {}

    def work() -> None:
        try:
            cursor = con.execute(statement)
            outcome["columns"] = [column[0] for column in cursor.description]
            outcome["types"] = [str(column[1]).lower() for column in cursor.description]
            outcome["rows"] = cursor.fetchmany(MAX_ROWS + 1)
        except Exception as error:
            outcome["error"] = error

    worker = threading.Thread(target=work, daemon=True)
    worker.start()
    worker.join(TIMEOUT_SECONDS)
    if worker.is_alive():
        con.interrupt()
        worker.join(TIMEOUT_SECONDS)
        raise QueryError(f"The query ran for more than {TIMEOUT_SECONDS} seconds, so I stopped it.")
    if "error" in outcome:
        raise QueryError(f"DuckDB said: {first_line(outcome['error'])}")
    rows = outcome["rows"]
    return box_table(outcome["columns"], outcome["types"], rows[:MAX_ROWS], truncated=len(rows) > MAX_ROWS)


def display_width(text: str) -> int:
    return sum(
        0 if unicodedata.combining(char) else 2 if unicodedata.east_asian_width(char) in "WF" else 1
        for char in text
    )


def clip(text: str, limit: int) -> str:
    if display_width(text) <= limit:
        return text
    kept = ""
    for char in text:
        if display_width(kept + char) > limit - 3:
            break
        kept += char
    return kept + "..."


def cell(value: object) -> str:
    if value is None:
        text = "NULL"
    elif isinstance(value, bool):
        text = "true" if value else "false"
    elif isinstance(value, float):
        text = str(round(value, 4))
    elif isinstance(value, datetime):
        text = value.isoformat(sep=" ")
    elif isinstance(value, date):
        text = value.isoformat()
    else:
        text = str(value)
    text = "".join(char if char.isprintable() else " " for char in text)
    return clip(inert(text), MAX_CELL_WIDTH)


def is_number(value: object) -> bool:
    return isinstance(value, (int, float, Decimal)) and not isinstance(value, bool)


def pad(text: str, width: int, align: str) -> str:
    gap = width - display_width(text)
    if align == "right":
        return " " * gap + text
    if align == "center":
        return " " * (gap // 2) + text + " " * (gap - gap // 2)
    return text + " " * gap


def box_table(columns: list[str], types: list[str], rows: list[tuple], truncated: bool = False) -> str:
    hidden = max(0, len(columns) - MAX_COLUMNS)
    columns, types = columns[:MAX_COLUMNS], types[:MAX_COLUMNS]
    header = [cell(name) for name in columns]
    kinds = [cell(name) for name in types]
    body = [[cell(value) for value in row[:MAX_COLUMNS]] for row in rows]
    right = [
        any(is_number(row[i]) for row in rows) and all(row[i] is None or is_number(row[i]) for row in rows)
        for i in range(len(columns))
    ]
    widths = [
        max([display_width(header[i]), display_width(kinds[i])] + [display_width(row[i]) for row in body])
        for i in range(len(columns))
    ]

    def rule(left: str, middle: str, end: str) -> str:
        return left + middle.join("─" * (width + 2) for width in widths) + end

    def line(cells: list[str], aligns: list[str]) -> str:
        return "│" + "│".join(f" {pad(text, widths[i], aligns[i])} " for i, text in enumerate(cells)) + "│"

    out = [rule("┌", "┬", "┐"), line(header, ["center"] * len(widths)), line(kinds, ["center"] * len(widths))]
    out.append(rule("├", "┼", "┤"))
    out += [line(row, ["right" if right[i] else "left" for i in range(len(widths))]) for row in body]
    out.append(rule("└", "┴", "┘"))

    count = f"{len(rows)} row" + ("" if len(rows) == 1 else "s")
    notes = [f"first {count}, more not shown" if truncated else count]
    if hidden:
        notes.append(f"{hidden} more column{'' if hidden == 1 else 's'} not shown")
    out.append(", ".join(notes))
    return "\n".join(out)


def fenced(text: str, info: str = "") -> str:
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    fence = "`" * max(3, longest + 1)
    return f"{fence}{info}\n{text}\n{fence}"


def inert(text: str) -> str:
    """Break HTML comment markers so user text cannot open or close a README section."""
    return text.replace("<!--", "<!- -").replace("-->", "- ->")


def replace_section(text: str, name: str, content: str) -> str:
    start, end = f"<!--START_SECTION:{name}-->", f"<!--END_SECTION:{name}-->"
    pattern = re.compile(f"{re.escape(start)}.*?{re.escape(end)}", re.S)
    if not pattern.search(text):
        raise ValueError(f"README.md has no {name} section")
    return pattern.sub(lambda _: f"{start}\n\n{content}\n\n{end}", text, count=1)


def refresh_profile(entry: dict) -> bool:
    """Write the query into the warehouse section and onto the profile when it is Friday."""
    import sys

    section = HERE / "section.md"
    if section.exists():
        section.write_text(
            replace_section(section.read_text(encoding="utf-8"), "warehouse-query", query_block(entry)),
            encoding="utf-8",
        )
    sys.path.insert(0, str(HERE.parent))
    from profile.rotate import active, apply

    apply()
    return active(datetime.now(TIMEZONE)) == "warehouse"


def query_block(entry: dict | None, example_result: str | None = None) -> str:
    if entry:
        ran_at = datetime.fromisoformat(entry["ran_at"]).astimezone(TIMEZONE)
        issue = entry["issue"]
        intro = (
            f"**Latest query** by [@{entry['user']}](https://github.com/{entry['user']}) "
            f"in [#{issue}]({REPO_URL}/issues/{issue}), {ran_at:%d %b %Y %H:%M} ICT"
        )
        sql, result = entry["sql"], entry["result"]
    else:
        intro = "**No visitor has queried it yet.** Here is an example the nightly build ran itself:"
        sql, result = EXAMPLE_SQL, example_result or ""
    return "\n\n".join([intro, fenced(inert(sql), "sql"), fenced(inert(result), "text")])


def load_json(path: Path, default: object) -> object:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def answer(title: str, body: str, user: str, number: int) -> str:
    if not title.strip().lower().startswith("query:"):
        return "This issue title does not start with `query:`, so I left it alone."
    if not LOGIN.fullmatch(user):
        return "I could not tell who opened this issue, so I skipped it."

    sql = extract_sql(body)
    now = datetime.now(TIMEZONE)
    today = now.date().isoformat()
    todays_queries = load_json(QUERY_LOG, {}).get(today, {})
    is_owner = user.lower() == OWNER.lower()
    previous = todays_queries.get(user.lower())
    if not is_owner and previous not in (None, number):
        return (
            f"Hi @{user}, you already ran today's query in #{previous}. The warehouse answers one query "
            "per person per day, Ho Chi Minh City time, so come back tomorrow."
        )

    try:
        result = run_select(open_warehouse(), sql)
    except QueryError as error:
        echo = sql if len(sql) <= MAX_SQL_CHARS else sql[:MAX_SQL_CHARS] + "\n..."
        return "\n\n".join([
            f"Hi @{user}, I could not run that query. {error}",
            fenced(echo or "(empty)", "sql"),
            "Errors do not count toward the one query per day, so feel free to open a new issue.",
        ])

    last = load_json(LAST_QUERY, None)
    same_issue = bool(last) and last.get("issue") == number
    entry = {
        "user": user,
        "issue": number,
        "sql": sql,
        "result": result,
        "ran_at": last["ran_at"] if same_issue else now.isoformat(timespec="seconds"),
    }
    write_json(LAST_QUERY, entry)
    if not is_owner:
        write_json(QUERY_LOG, {today: {**todays_queries, user.lower(): number}})
    shown_now = refresh_profile(entry)

    where = (
        "Your query is now on my profile until the next visitor replaces it."
        if shown_now
        else "Your query is saved, and it will show on my profile on Friday, when the warehouse takes the top of the page."
    )
    return "\n\n".join([
        f"Hi @{user}, thanks for querying my warehouse. You asked:",
        fenced(sql, "sql"),
        "DuckDB returned:",
        fenced(result, "text"),
        f"{where} The tables refresh every night at 07:40 Ho Chi Minh City time.",
    ])


def main() -> None:
    reply = answer(
        title=os.environ.get("ISSUE_TITLE", ""),
        body=os.environ.get("ISSUE_BODY", ""),
        user=os.environ.get("ISSUE_USER", ""),
        number=int(os.environ["ISSUE_NUMBER"]),
    )
    reply_path = Path(os.environ.get("REPLY_PATH") or HERE / "reply.md")
    reply_path.write_text(reply + "\n", encoding="utf-8")
    print(reply)


if __name__ == "__main__":
    main()
