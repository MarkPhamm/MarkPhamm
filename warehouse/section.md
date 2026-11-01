My GitHub profile is a data warehouse. Every night a real [dbt project](https://github.com/MarkPhamm/MarkPhamm/tree/main/warehouse) loads my GitHub and WakaTime activity into DuckDB, tests it, and builds this section from the marts. You can query it.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="warehouse/assets/lineage-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="warehouse/assets/lineage-light.svg">
  <img src="warehouse/assets/lineage-light.svg" width="100%" alt="dbt lineage: 5 sources and seeds flow through staging and intermediate models into 4 marts, 15 tests">
</picture>

`dbt build · 11 models · 15 tests · PASS 13 · WARN 1 · FAIL 1 · 01 Nov 2026 14:16 ICT`

```text
$ dbt build --exclude tag:personality
PASS  not_null         fct_contributions.day
PASS  unique           fct_contributions.day
PASS  non_negative     fct_contributions.contributions
PASS  assert_date_spine_has_365_days
PASS  unique           fct_coding_week.language
PASS  not_null         dim_repos.repo_name
PASS  unique           dim_repos.repo_name
PASS  non_negative     dim_repos.stars
PASS  accepted_values  dim_repos.status
PASS  not_null         dim_career.company
PASS  not_null         dim_career.start_date

$ dbt test --select tag:personality
PASS  assert_mark_touched_grass        busiest day was Wednesday with 37 contributions
PASS  assert_shipped_this_week         135 contributions in the last 7 days
WARN  assert_weekends_are_for_resting  19 contributions on Sat 31 Oct and 6 on Sun 01 Nov
FAIL  assert_sql_share_below_25_pct    SQL was 28.12% of this week's coding
```

<a href="https://github.com/MarkPhamm/MarkPhamm/issues/new?title=query%3A%20&amp;body=Write%20one%20SELECT%20in%20the%20sql%20block%20below%20and%20submit%20the%20issue.%20A%20GitHub%20Action%20runs%20it%20against%20my%20warehouse%20in%20DuckDB%20and%20replies%20here%20with%20the%20result.%0A%0A%60%60%60sql%0Aselect%20repo_name%2C%20stars%20from%20dim_repos%20order%20by%20stars%20desc%20limit%205%3B%0A%60%60%60%0A%0ATables%3A%20fct_contributions%2C%20fct_coding_week%2C%20dim_repos%2C%20dim_career.%20One%20query%20per%20person%20per%20day."><img src="https://img.shields.io/badge/Query_my_warehouse-FF694B?style=for-the-badge" alt="Query my warehouse"/></a>

Open an issue with one `select` and a GitHub Action runs it in DuckDB against these tables, then replies with the result:

- `fct_contributions` (365 rows): day, contributions, coding_hours, is_weekend
- `fct_coding_week` (6 rows): language, hours, share_pct
- `dim_repos` (81 rows): repo_name, stars, language, commits_this_year, status, pushed_at, url
- `dim_career` (8 rows): company, role, start_date, end_date, is_current, months, url

<!--START_SECTION:warehouse-query-->

**No visitor has queried it yet.** Here is an example the nightly build ran itself:

```sql
select repo_name, stars, commits_this_year, status
from dim_repos
order by stars desc
limit 5;
```

```text
┌──────────────────────────┬────────┬───────────────────┬────────────┐
│        repo_name         │ stars  │ commits_this_year │   status   │
│         varchar          │ bigint │      bigint       │  varchar   │
├──────────────────────────┼────────┼───────────────────┼────────────┤
│ dbt-Fundamental          │     37 │                 9 │ active     │
│ local_streaming_pipeline │     22 │                56 │ maintained │
│ skytrax_reviews          │     13 │                34 │ active     │
│ local_warehouse_pipeline │     11 │                18 │ active     │
│ quickdbd-cli             │      7 │               207 │ active     │
└──────────────────────────┴────────┴───────────────────┴────────────┘
5 rows
```

<!--END_SECTION:warehouse-query-->
