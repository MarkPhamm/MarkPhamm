"""Draw the lineage, export the marts and rewrite the warehouse section of README.md."""

import json
import statistics
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

import duckdb

import query

HERE = Path(__file__).resolve().parent
TARGET = HERE / "target"
RAW = HERE / "raw"
ASSETS = HERE / "assets"
DATABASE = HERE / "mark.duckdb"
PROJECT_URL = f"{query.REPO_URL}/tree/main/warehouse"

MARTS = {
    "fct_contributions": "day",
    "fct_coding_week": "hours desc, language",
    "dim_repos": "stars desc, repo_name",
    "dim_career": "start_date, company",
}
LAYERS = ["sources & seeds", "staging", "intermediate", "marts"]
LAYER_COLORS = ["green", "blue", "purple", "orange"]
STATUS_LABELS = {"pass": "PASS", "warn": "WARN", "fail": "FAIL", "error": "ERROR", "skipped": "SKIP"}
STATUS_ORDER = ["PASS", "WARN", "FAIL", "ERROR", "SKIP"]

THEMES = {
    "light": {
        "bg": "#ffffff", "text": "#1f2328", "muted": "#59636e", "border": "#d1d9e0", "edge": "#8c959f",
        "green": "#1a7f37", "blue": "#0969da", "purple": "#8250df", "orange": "#bc4c00",
        "PASS": "#1a7f37", "WARN": "#9a6700", "FAIL": "#d1242f", "ERROR": "#d1242f", "SKIP": "#59636e",
        "tint": 0.07,
    },
    "dark": {
        "bg": "#0d1117", "text": "#e6edf3", "muted": "#9198a1", "border": "#3d444d", "edge": "#656c76",
        "green": "#3fb950", "blue": "#4493f8", "purple": "#ab7df8", "orange": "#f0883e",
        "PASS": "#3fb950", "WARN": "#d29922", "FAIL": "#f85149", "ERROR": "#f85149", "SKIP": "#9198a1",
        "tint": 0.12,
    },
}

MONO = "ui-monospace, SFMono-Regular, Menlo, monospace"
SANS = "-apple-system, Segoe UI, Helvetica, Arial, sans-serif"
NAME_SIZE = 13
META_SIZE = 11
NODE_HEIGHT = 50
NODE_PADDING = 14
ROW_GAP = 14
COLUMN_GAP = 56
MARGIN = 22
NODES_TOP = 100


@dataclass
class Node:
    uid: str
    name: str
    layer: int
    kind: str
    rows: int
    parents: list[str]
    statuses: list[str] = field(default_factory=list)

    @property
    def meta(self) -> str:
        return f"{self.kind} · {plural(self.rows, 'row')}"

    @property
    def tests_label(self) -> str:
        return plural(len(self.statuses), "test") if self.statuses else ""


@dataclass
class TestResult:
    name: str
    check: str
    target: str
    status: str
    personality: bool
    sort_key: tuple


def plural(count: int, word: str) -> str:
    return f"{count} {word}" + ("" if count == 1 else "s")


def attr(value: object) -> str:
    return escape(str(value), {'"': "&quot;"})


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def worst(statuses: list[str]) -> str:
    return max(statuses, key=STATUS_ORDER.index)


def load_graph(manifest: dict, con: duckdb.DuckDBPyConnection) -> dict[str, Node]:
    nodes = {}
    for uid, source in manifest["sources"].items():
        raw_file = RAW / f"{source['source_name']}_{source['name']}.json"
        rows = len(load_json(raw_file)) if raw_file.exists() else 0
        name = f"{source['source_name']}.{source['name']}"
        nodes[uid] = Node(uid, name, 0, "raw json", rows, [])
    for uid, node in manifest["nodes"].items():
        if node["resource_type"] not in ("seed", "model"):
            continue
        rows = con.execute(f'select count(*) from main."{node["name"]}"').fetchone()[0]
        if node["resource_type"] == "seed":
            nodes[uid] = Node(uid, node["name"], 0, "seed csv", rows, [])
        else:
            layer = LAYERS.index(Path(node["original_file_path"]).parts[1])
            parents = node["depends_on"]["nodes"]
            nodes[uid] = Node(uid, node["name"], layer, node["config"]["materialized"], rows, parents)
    return nodes


def load_tests(manifest: dict, nodes: dict[str, Node]) -> list[TestResult]:
    statuses = {}
    for path in (TARGET / "run_results_build.json", TARGET / "run_results.json"):
        if path.exists():
            for result in load_json(path)["results"]:
                statuses[result["unique_id"]] = STATUS_LABELS.get(result["status"], result["status"].upper())

    mart_order = list(MARTS)
    tests = []
    for uid, node in manifest["nodes"].items():
        if node["resource_type"] != "test" or uid not in statuses:
            continue
        depends_on = node["depends_on"]["nodes"]
        model = nodes[depends_on[0]].name if depends_on else ""
        metadata = node.get("test_metadata")
        if metadata:
            column = node.get("column_name") or ""
            columns = list(manifest["nodes"][node["attached_node"]]["columns"])
            check, target = metadata["name"], f"{model}.{column}"
            position = columns.index(column) if column in columns else len(columns)
        else:
            check, target, position = node["name"], "", 999
        rank = mart_order.index(model) if model in mart_order else len(mart_order)
        tests.append(
            TestResult(
                name=node["name"],
                check=check,
                target=target,
                status=statuses[uid],
                personality="personality" in node["tags"],
                sort_key=(rank, position, check),
            )
        )
        for parent in depends_on:
            if parent in nodes:
                nodes[parent].statuses.append(statuses[uid])
    return sorted(tests, key=lambda test: test.sort_key)


def hours_minutes(hours: float) -> str:
    minutes = round(hours * 60)
    return f"{minutes // 60}h {minutes % 60:02d}m"


def grass_detail(week: list[tuple]) -> str:
    coded = [row for row in week if row[2] is not None]
    long_days = [row for row in coded if row[2] > 10]
    if long_days:
        day, _, hours = max(long_days, key=lambda row: row[2])
        return f"coded {hours_minutes(hours)} on {day:%A}"
    busy_days = [row for row in week if row[2] is None and row[1] > 40]
    if busy_days:
        day, contributions, _ = max(busy_days, key=lambda row: row[1])
        return f"{contributions} contributions on {day:%A}, with no WakaTime data to argue"
    if coded:
        day, _, hours = max(coded, key=lambda row: row[2])
        return f"longest day was {hours_minutes(hours)} of coding, on {day:%A}"
    day, contributions, _ = max(week, key=lambda row: row[1])
    return f"busiest day was {day:%A} with {contributions} contributions"


def weekend_detail(weekend: list[tuple]) -> str:
    if not any(contributions for _, contributions in weekend):
        return "no contributions on " + " or ".join(f"{day:%a %d %b}" for day, _ in weekend)
    parts = [f"{contributions} on {day:%a %d %b}" for day, contributions in weekend]
    first_count = weekend[0][1]
    parts[0] = f"{plural(first_count, 'contribution')} on {weekend[0][0]:%a %d %b}"
    return " and ".join(parts)


def personality_details(con: duckdb.DuckDBPyConnection) -> dict[str, str]:
    week = con.execute(
        "select day, contributions, coding_hours from fct_contributions where day > current_date - 7 order by day"
    ).fetchall()
    sql_share = con.execute("select share_pct from fct_coding_week where language = 'SQL'").fetchone()
    weekend = con.execute(
        """
        with last_saturday as (
            select max(day) as saturday from fct_contributions where isodow(day) = 6
        )
        select day, contributions
        from fct_contributions cross join last_saturday
        where day between saturday and saturday + 1
        order by day
        """
    ).fetchall()
    shipped = sum(row[1] for row in week)
    return {
        "assert_mark_touched_grass": grass_detail(week),
        "assert_sql_share_below_25_pct": (
            f"SQL was {sql_share[0]:.2f}% of this week's coding" if sql_share else "no SQL at all this week, suspicious"
        ),
        "assert_shipped_this_week": f"{plural(shipped, 'contribution')} in the last 7 days",
        "assert_weekends_are_for_resting": weekend_detail(weekend),
    }


def order_columns(columns: list[list[str]], nodes: dict[str, Node]) -> None:
    children = {uid: [] for uid in nodes}
    for node in nodes.values():
        for parent in node.parents:
            if parent in children:
                children[parent].append(node.uid)

    position = {}

    def index() -> None:
        for column in columns:
            for i, uid in enumerate(column):
                position[uid] = (i + 0.5) / len(column)

    def barycenter(uid: str, neighbours: list[str]) -> float:
        known = [position[other] for other in neighbours if other in position]
        return statistics.mean(known) if known else position[uid]

    for column in columns:
        column.sort(key=lambda uid: nodes[uid].name)
    index()
    for _ in range(4):
        for column in columns[1:]:
            column.sort(key=lambda uid: barycenter(uid, nodes[uid].parents))
            index()
        for column in reversed(columns[:-1]):
            column.sort(key=lambda uid: barycenter(uid, children[uid]))
            index()


def place_rows(columns: list[list[str]], nodes: dict[str, Node]) -> dict[str, float]:
    pitch = NODE_HEIGHT + ROW_GAP
    tallest = max(range(len(columns)), key=lambda i: len(columns[i]))
    bottom = (len(columns[tallest]) - 1) * pitch
    children = {uid: [n.uid for n in nodes.values() if uid in n.parents] for uid in nodes}
    y = {uid: i * pitch for i, uid in enumerate(columns[tallest])}

    def settle(column: list[str], neighbours: dict[str, list[str]]) -> None:
        ideal = {}
        for i, uid in enumerate(column):
            known = [y[other] for other in neighbours[uid] if other in y]
            ideal[uid] = statistics.mean(known) if known else i * pitch
        previous = None
        for uid in column:
            y[uid] = ideal[uid] if previous is None else max(ideal[uid], y[previous] + pitch)
            previous = uid
        following = None
        for uid in reversed(column):
            limit = bottom if following is None else y[following] - pitch
            y[uid] = max(0, min(y[uid], limit))
            following = uid

    parents = {uid: node.parents for uid, node in nodes.items()}
    for column in columns[tallest + 1 :]:
        settle(column, parents)
    for column in reversed(columns[:tallest]):
        settle(column, children)
    return y


def mix(color: str, background: str, amount: float) -> str:
    front = [int(color[i : i + 2], 16) for i in (1, 3, 5)]
    back = [int(background[i : i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(a * amount + b * (1 - amount)):02x}" for a, b in zip(front, back, strict=True))


def mono_width(text: str, size: float) -> float:
    return len(text) * size * 0.61


def sans_width(text: str, size: float) -> float:
    return len(text) * size * 0.56


def column_width(column: list[str], nodes: dict[str, Node]) -> float:
    widest = 0.0
    for uid in column:
        node = nodes[uid]
        meta = sans_width(node.meta, META_SIZE)
        if node.tests_label:
            meta += 24 + sans_width(node.tests_label, META_SIZE) + 12
        widest = max(widest, mono_width(node.name, NAME_SIZE), meta)
    return round(widest + 2 * NODE_PADDING)


def lineage_svg(nodes: dict[str, Node], tests: list[TestResult], theme_name: str) -> str:
    theme = THEMES[theme_name]
    columns = [[uid for uid, node in nodes.items() if node.layer == layer] for layer in range(len(LAYERS))]
    order_columns(columns, nodes)
    rows = place_rows(columns, nodes)

    widths = [column_width(column, nodes) for column in columns]
    lefts = []
    x = MARGIN
    for width in widths:
        lefts.append(x)
        x += width + COLUMN_GAP
    svg_width = round(x - COLUMN_GAP + MARGIN)
    svg_height = round(NODES_TOP + max(rows.values()) + NODE_HEIGHT + MARGIN)
    box = {}
    for layer, column in enumerate(columns):
        for uid in column:
            box[uid] = (lefts[layer], NODES_TOP + rows[uid], widths[layer])

    counts = {label: sum(test.status == label for test in tests) for label in STATUS_ORDER}
    sources = sum(1 for node in nodes.values() if node.layer == 0)
    models = len(nodes) - sources
    title = f"dbt lineage of mark_warehouse: {sources} sources and seeds, {models} models, {len(tests)} tests"

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{svg_height}" '
        f'viewBox="0 0 {svg_width} {svg_height}" role="img" aria-label="{attr(title)}">',
        f"<title>{escape(title)}</title>",
        f'<rect x="0.5" y="0.5" width="{svg_width - 1}" height="{svg_height - 1}" rx="12" '
        f'fill="{theme["bg"]}" stroke="{theme["border"]}"/>',
        f'<text x="{MARGIN}" y="42" fill="{theme["text"]}">'
        f'<tspan font-family="{MONO}" font-size="16" font-weight="700">mark_warehouse</tspan>'
        f'<tspan dx="12" font-family="{SANS}" font-size="13" fill="{theme["muted"]}">'
        f"dbt lineage, rebuilt every night from target/manifest.json</tspan></text>",
    ]

    legend = [f'<tspan fill="{theme["muted"]}" font-weight="400">{plural(len(tests), "test")}</tspan>']
    legend += [
        f'<tspan dx="12" fill="{theme[label]}">{counts[label]} {label.lower()}</tspan>'
        for label in STATUS_ORDER
        if counts[label]
    ]
    out.append(
        f'<text x="{svg_width - MARGIN}" y="42" text-anchor="end" font-family="{SANS}" font-size="12" '
        f'font-weight="600">{"".join(legend)}</text>'
    )

    for layer, heading in enumerate(LAYERS):
        out.append(
            f'<text x="{lefts[layer]}" y="80" font-family="{SANS}" font-size="11" font-weight="700" '
            f'letter-spacing="1" fill="{theme[LAYER_COLORS[layer]]}">{escape(heading.upper())}</text>'
        )

    for node in nodes.values():
        for parent in node.parents:
            if parent not in box:
                continue
            px, py, pw = box[parent]
            cx, cy, _ = box[node.uid]
            x1, y1 = px + pw, py + NODE_HEIGHT / 2
            x2, y2 = cx, cy + NODE_HEIGHT / 2
            bend = (x2 - x1) / 2
            out.append(
                f'<path d="M{x1:.1f},{y1:.1f} C{x1 + bend:.1f},{y1:.1f} {x2 - bend:.1f},{y2:.1f} {x2:.1f},{y2:.1f}" '
                f'fill="none" stroke="{theme["edge"]}" stroke-width="1.5"/>'
            )
            out.append(f'<circle cx="{x2:.1f}" cy="{y2:.1f}" r="3" fill="{theme["edge"]}"/>')

    for uid, (x, y, width) in box.items():
        node = nodes[uid]
        color = theme[LAYER_COLORS[node.layer]]
        out.append(
            f'<rect x="{x}" y="{y}" width="{width}" height="{NODE_HEIGHT}" rx="8" '
            f'fill="{mix(color, theme["bg"], theme["tint"])}" stroke="{color}" stroke-width="1.25"/>'
        )
        out.append(
            f'<text x="{x + NODE_PADDING}" y="{y + 21}" font-family="{MONO}" font-size="{NAME_SIZE}" '
            f'font-weight="600" fill="{theme["text"]}">{escape(node.name)}</text>'
        )
        out.append(
            f'<text x="{x + NODE_PADDING}" y="{y + 39}" font-family="{SANS}" font-size="{META_SIZE}" '
            f'fill="{theme["muted"]}">{escape(node.meta)}</text>'
        )
        if node.statuses:
            right = x + width - NODE_PADDING
            out.append(
                f'<text x="{right}" y="{y + 39}" text-anchor="end" font-family="{SANS}" font-size="{META_SIZE}" '
                f'fill="{theme["muted"]}">{escape(node.tests_label)}</text>'
            )
            dot_x = right - sans_width(node.tests_label, META_SIZE) - 8
            out.append(f'<circle cx="{dot_x:.1f}" cy="{y + 35}" r="3.5" fill="{theme[worst(node.statuses)]}"/>')

    out.append("</svg>")
    return "\n".join(out) + "\n"


def export_marts(con: duckdb.DuckDBPyConnection) -> None:
    query.EXPORTS.mkdir(exist_ok=True)
    for name, order in MARTS.items():
        path = query.EXPORTS / f"{name}.csv"
        con.execute(f"copy (select * from main.{name} order by {order}) to '{path}' (header, delimiter ',')")


def build_summary(models: int, tests: list[TestResult]) -> str:
    built_at = datetime.fromisoformat(load_json(TARGET / "run_results_build.json")["metadata"]["generated_at"])
    counts = {label: sum(test.status == label for test in tests) for label in STATUS_ORDER}
    parts = ["dbt build", plural(models, "model"), plural(len(tests), "test")]
    parts += [f"{label} {counts[label]}" for label in STATUS_ORDER if counts[label] or label == "PASS"]
    parts.append(f"{built_at.astimezone(query.TIMEZONE):%d %b %Y %H:%M} ICT")
    return " · ".join(parts)


def test_report(tests: list[TestResult], details: dict[str, str]) -> str:
    data = [test for test in tests if not test.personality]
    personality = [test for test in tests if test.personality]
    check_width = max((len(test.check) for test in data if test.target), default=0)
    lines = ["$ dbt build --exclude tag:personality"]
    for test in data:
        target = f"{test.check:<{check_width}}  {test.target}" if test.target else test.check
        lines.append(f"{test.status:<5} {target}".rstrip())
    if personality:
        name_width = max(len(test.name) for test in personality)
        lines += ["", "$ dbt test --select tag:personality"]
        for test in personality:
            lines.append(f"{test.status:<5} {test.name:<{name_width}}  {details.get(test.name, '')}".rstrip())
    return "\n".join(lines)


def table_list(warehouse: duckdb.DuckDBPyConnection) -> list[str]:
    lines = []
    for name in MARTS:
        columns = [row[0] for row in warehouse.execute(f"describe {name}").fetchall()]
        rows = warehouse.execute(f"select count(*) from {name}").fetchone()[0]
        lines.append(f"- `{name}` ({plural(rows, 'row')}): {', '.join(columns)}")
    return lines


def query_link() -> str:
    body = "\n".join(
        [
            "Write one SELECT in the sql block below and submit the issue. A GitHub Action runs it "
            "against my warehouse in DuckDB and replies here with the result.",
            "",
            "```sql",
            "select repo_name, stars from dim_repos order by stars desc limit 5;",
            "```",
            "",
            f"Tables: {', '.join(MARTS)}. One query per person per day.",
        ]
    )
    params = urllib.parse.urlencode({"title": "query: ", "body": body}, quote_via=urllib.parse.quote)
    return f"{query.REPO_URL}/issues/new?{params}"


def readme_block(summary: str, report: str, tables: list[str], query_section: str, alt: str) -> str:
    badge = "https://img.shields.io/badge/Query_my_warehouse-FF694B?style=for-the-badge"
    lines = [
        "My GitHub profile is a data warehouse. Every night a real "
        f"[dbt project]({PROJECT_URL}) loads my GitHub and WakaTime activity into DuckDB, "
        "tests it, and builds this section from the marts. You can query it.",
        "",
        "<picture>",
        '  <source media="(prefers-color-scheme: dark)" srcset="warehouse/assets/lineage-dark.svg">',
        '  <source media="(prefers-color-scheme: light)" srcset="warehouse/assets/lineage-light.svg">',
        f'  <img src="warehouse/assets/lineage-light.svg" width="100%" alt="{attr(alt)}">',
        "</picture>",
        "",
        f"`{summary}`",
        "",
        query.fenced(report, "text"),
        "",
        f'<a href="{attr(query_link())}"><img src="{badge}" alt="Query my warehouse"/></a>',
        "",
        "Open an issue with one `select` and a GitHub Action runs it in DuckDB against these tables, "
        "then replies with the result:",
        "",
        *tables,
        "",
        "<!--START_SECTION:warehouse-query-->",
        "",
        query_section,
        "",
        "<!--END_SECTION:warehouse-query-->",
    ]
    return "\n".join(lines)


def write_readme(block: str) -> None:
    readme = query.README.read_text(encoding="utf-8")
    if "<!--START_SECTION:warehouse-->" not in readme:
        empty = "<!--START_SECTION:warehouse-->\n<!--END_SECTION:warehouse-->"
        readme = readme.replace("</picture>\n", f"</picture>\n{empty}\n", 1)
    query.README.write_text(query.replace_section(readme, "warehouse", block), encoding="utf-8")


def main() -> None:
    manifest = load_json(TARGET / "manifest.json")
    con = duckdb.connect(str(DATABASE), read_only=True)
    nodes = load_graph(manifest, con)
    tests = load_tests(manifest, nodes)
    details = personality_details(con)

    ASSETS.mkdir(exist_ok=True)
    for theme in THEMES:
        (ASSETS / f"lineage-{theme}.svg").write_text(lineage_svg(nodes, tests, theme), encoding="utf-8")

    export_marts(con)
    con.close()

    warehouse = query.open_warehouse()
    last = query.load_json(query.LAST_QUERY, None)
    example = None if last else query.run_select(warehouse, query.EXAMPLE_SQL)
    query_section = query.query_block(last, example)

    models = sum(1 for node in nodes.values() if node.layer > 0)
    sources = len(nodes) - models
    alt = (
        f"dbt lineage: {sources} sources and seeds flow through staging and intermediate models "
        f"into {len(MARTS)} marts, {len(tests)} tests"
    )
    summary = build_summary(models, tests)
    write_readme(readme_block(summary, test_report(tests, details), table_list(warehouse), query_section, alt))
    print(f"rendered {models} models, {len(tests)} tests, lineage in {ASSETS.relative_to(HERE)}")


if __name__ == "__main__":
    main()
