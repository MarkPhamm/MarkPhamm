![Cover For Notion](https://github.com/user-attachments/assets/7a3c0f97-1fd4-481c-a37d-56fb639e8537)

<picture>
  <source media="(prefers-color-scheme: dark)"
          srcset="https://readme-typing-svg.demolab.com?font=Inconsolata&weight=500&size=50&duration=1500&pause=50&color=FFFFFF&multiline=true&repeat=false&width=1300&height=140&lines=I+wrote+too+much+SQL+...+%F0%9F%99%81;Probably+need+to+touch+some+grass+%F0%9F%8C%B1">
  <source media="(prefers-color-scheme: light)"
          srcset="https://readme-typing-svg.demolab.com?font=Inconsolata&weight=500&size=50&duration=1500&pause=50&color=000000&multiline=true&repeat=false&width=1300&height=140&lines=I+wrote+too+much+SQL+...+%F0%9F%99%81;Probably+need+to+touch+some+grass+%F0%9F%8C%B1">
  <img src="https://readme-typing-svg.demolab.com?font=Inconsolata&weight=500&size=50&duration=1500&pause=50&color=FFFFFF&multiline=true&repeat=false&width=1300&height=140&lines=I+wrote+too+much+SQL+...+%F0%9F%99%81;Probably+need+to+touch+some+grass+%F0%9F%8C%B1">
</picture>
<!--START_SECTION:warehouse-->

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

<!--END_SECTION:warehouse-->

## 🧠 About Me <img src="https://user-images.githubusercontent.com/73097560/115834477-dbab4500-a447-11eb-908a-139a6edaec5c.gif">

<blockquote align="center">
  <b><i>"Analytics isn't just my job - it's my obsession. Scroll down and see for yourself"</i></b>
</blockquote>

<p align="center">
  <img src="koi/koi.gif" width="256" alt="My koi, redrawn every night from my GitHub activity" />
</p>

<p align="center">
  <a href="https://www.linkedin.com/in/minhbphamm/" target="_blank">
    <img src="https://img.shields.io/badge/LinkedIn-Profile-blue?style=for-the-badge&logo=linkedin" />
  </a>
  <a href="https://leetcode.com/u/markphammm/" target="_blank">
    <img src="https://img.shields.io/badge/LeetCode-Profile-orange?style=for-the-badge&logo=leetcode" />
  </a>
  <a href="https://platform.stratascratch.com/user/SmartPersonality1862" target="_blank">
    <img src="https://img.shields.io/badge/StrataScratch-Profile-00A79D?style=for-the-badge&logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAAAdVBMVEUAAAD///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////9jhTEsAAAAK3RSTlMAAQIDBAUGBwgJCgsMDQ8QERITFBUWFxgZGhscHR4fICEiIyQmJygpKiuzg1ZnAAAAPUlEQVR42jXJRw6AIAwEwG9r2+9fZbCllPw/6wJWiRMwCqbk9zMBoIRlpBKR6FQAoipxkAdRHWuMtk5+egAtI7AmZpjE9AAAAAElFTkSuQmCC" alt="StrataScratch logo" />
  </a>
</p>

<div align="center">
  
[![wakatime](https://wakatime.com/badge/user/894cf02a-9974-42d0-acde-603cdd98fe17.svg)](https://wakatime.com/@894cf02a-9974-42d0-acde-603cdd98fe17)
![Working on](https://img.shields.io/badge/Working%20On-Building%20Data%20Pipelines-blue)
![Learning](https://img.shields.io/badge/Learning-Advanced%20dbt%20&%20Jinja⚡-orange)
![visitors](https://visitor-badge.laobi.icu/badge?page_id=MarkPhamm)
</div>

---

## 💼 Experience <img src="https://user-images.githubusercontent.com/73097560/115834477-dbab4500-a447-11eb-908a-139a6edaec5c.gif">

<div align="center">
  <table width="100%">
    <tr>
      <td align="center" valign="top" width="11%">
        <sub>May 2022 - Sep 2022</sub><br /><br />
        <img src="https://www.google.com/s2/favicons?sz=32&domain=kpim.vn" width="24" height="24" /><br /><br />
        <a href="https://kpim.vn/"><b>KPIM</b></a><br />
        <sub>Data Science</sub>
      </td>
      <td align="center" valign="middle" width="1%">➔</td>
      <td align="center" valign="top" width="11%">
        <sub>May 2022 - Sep 2022</sub><br /><br />
        <img src="https://www.google.com/s2/favicons?sz=32&domain=napas.com.vn" width="24" height="24" /><br /><br />
        <a href="https://en.napas.com.vn/"><b>NAPAS</b></a><br />
        <sub>Data Analyst</sub>
      </td>
      <td align="center" valign="middle" width="1%">➔</td>
      <td align="center" valign="top" width="11%">
        <sub>Jan 2023 - May 2023</sub><br /><br />
        <img src="https://www.google.com/s2/favicons?sz=32&domain=corning.com" width="24" height="24" /><br /><br />
        <a href="https://www.corning.com/"><b>Corning Inc.</b></a><br />
        <sub>Data Analyst</sub>
      </td>
      <td align="center" valign="middle" width="1%">➔</td>
      <td align="center" valign="top" width="11%">
        <sub>Jan 2024 - May 2024</sub><br /><br />
        <img src="https://www.google.com/s2/favicons?sz=32&domain=techsmith.com" width="24" height="24" /><br /><br />
        <a href="https://www.techsmith.com/"><b>TechSmith Corp</b></a><br />
        <sub>BI Engineer</sub>
      </td>
      <td align="center" valign="middle" width="1%">➔</td>
      <td align="center" valign="top" width="11%">
        <sub>May 2024 - Aug 2024</sub><br /><br />
        <img src="https://www.google.com/s2/favicons?sz=32&domain=lazard.com" width="24" height="24" /><br /><br />
        <a href="https://www.lazard.com/"><b>Lazard</b></a><br />
        <sub>Data Engineer</sub>
      </td>
      <td align="center" valign="middle" width="1%">➔</td>
      <td align="center" valign="top" width="11%">
        <sub>May 2025 - Aug 2026</sub><br /><br />
        <img src="https://www.google.com/s2/favicons?sz=32&domain=insurify.com" width="24" height="24" /><br /><br />
        <a href="https://insurify.com/"><b>Insurify</b></a><br />
        <sub>Analytics Engineer</sub>
      </td>
      <td align="center" valign="middle" width="1%">➔</td>
      <td align="center" valign="top" width="11%">
        <sub>May 2025 - </sub><img src="https://img.shields.io/badge/Present-2ea44f?style=flat-square" height="14" valign="middle" /><br /><br />
        <img src="https://www.google.com/s2/favicons?sz=32&domain=facebook.com" width="24" height="24" /><br /><br />
        <a href="https://xomdata.com/"><b>Xóm Data</b></a><br />
        <sub>Builder</sub>
      </td>
      <td align="center" valign="middle" width="1%">➔</td>
      <td align="center" valign="top" width="11%">
        <sub>Aug 2026 - </sub><img src="https://img.shields.io/badge/Present-2ea44f?style=flat-square" height="14" valign="middle" /><br /><br />
        <img src="https://www.google.com/s2/favicons?sz=32&domain=infinitelambda.com" width="24" height="24" /><br /><br />
        <a href="https://infinitelambda.com/"><b>Infinite Lambda</b></a><br />
        <sub>Senior Analytics Engineer</sub>
      </td>
    </tr>
  </table>
</div>

---

## 🛠️ Techstack &amp; Ecosystem <img src="https://user-images.githubusercontent.com/73097560/115834477-dbab4500-a447-11eb-908a-139a6edaec5c.gif">

<div align="center">
  <h3>🛠️ Tech Stack &amp; Reference Logos</h3>
  <table width="100%">
    <tr>
      <td width="25%"><b>🏢 Data Warehouse</b></td>
      <td width="75%">
        <img src="https://img.shields.io/badge/Snowflake-29B5E8?style=flat-square&logo=snowflake&logoColor=white" alt="Snowflake"/>
        <img src="https://img.shields.io/badge/Redshift-8C4FFF?style=flat-square&logo=amazonredshift&logoColor=white" alt="Redshift"/>
        <img src="https://img.shields.io/badge/BigQuery-6699FF?style=flat-square&logo=google-bigquery&logoColor=white" alt="BigQuery"/>
        <img src="https://img.shields.io/badge/ClickHouse-FFCC01?style=flat-square&logo=clickhouse&logoColor=black" alt="ClickHouse"/>
      </td>
    </tr>
    <tr>
      <td><b>🌊 Data Lakehouse</b></td>
      <td>
        <img src="https://img.shields.io/badge/Databricks-FF3621?style=flat-square&logo=databricks&logoColor=white" alt="Databricks"/>
        <img src="https://img.shields.io/badge/DuckDB-FFF000?style=flat-square&logo=duckdb&logoColor=black" alt="DuckDB"/>
        <img src="https://img.shields.io/badge/MotherDuck-FFD400?style=flat-square&logo=duckdb&logoColor=black" alt="MotherDuck"/>
        <img src="https://img.shields.io/badge/Iceberg-1E88E5?style=flat-square&logo=apacheiceberg&logoColor=white" alt="Iceberg"/>
        <img src="https://img.shields.io/badge/Delta_Lake-00ADD4?style=flat-square&logo=delta&logoColor=white" alt="Delta Lake"/>
        <img src="https://img.shields.io/badge/Trino-DD00A1?style=flat-square&logo=trino&logoColor=white" alt="Trino"/>
        <img src="https://img.shields.io/badge/PrestoDB-5890FF?style=flat-square&logo=presto&logoColor=white" alt="PrestoDB"/>
        <img src="https://img.shields.io/badge/Pinot-000000?style=flat-square&logo=apache&logoColor=white" alt="Pinot"/>
        <img src="https://img.shields.io/badge/Hive-FDEE21?style=flat-square&logo=apachehive&logoColor=black" alt="Hive"/>
        <img src="https://img.shields.io/badge/HDFS-66CCFF?style=flat-square&logo=apachehadoop&logoColor=black" alt="HDFS"/>
      </td>
    </tr>
    <tr>
      <td><b>🔄 Data Processing &amp; Transformation</b></td>
      <td>
        <img src="https://img.shields.io/badge/Apache_Spark-E25A1C?style=flat-square&logo=apache-spark&logoColor=white" alt="Apache Spark"/>
        <img src="https://img.shields.io/badge/Spark_Structured_Streaming-E25A1C?style=flat-square&logo=apache-spark&logoColor=white" alt="Spark Structured Streaming"/>
        <img src="https://img.shields.io/badge/Flink-E6526F?style=flat-square&logo=apacheflink&logoColor=white" alt="Flink"/>
        <img src="https://img.shields.io/badge/Alteryx-0078D4?style=flat-square&logo=alteryx&logoColor=white" alt="Alteryx"/>
        <img src="https://img.shields.io/badge/Kafka-231F20?style=flat-square&logo=apachekafka&logoColor=white" alt="Kafka"/>
        <img src="https://img.shields.io/badge/Kinesis-FF9900?style=flat-square&logo=amazonaws&logoColor=white" alt="Kinesis"/>
        <img src="https://img.shields.io/badge/Google_Pub%2FSub-4285F4?style=flat-square&logo=googlecloud&logoColor=white" alt="Google Pub/Sub"/>
        <img src="https://img.shields.io/badge/CDC-4B8BBE?style=flat-square&logo=debezium&logoColor=white" alt="CDC"/>
        <img src="https://img.shields.io/badge/dbt_Core-FF694B?style=flat-square&logo=dbt&logoColor=white" alt="dbt Core"/>
      </td>
    </tr>
    <tr>
      <td><b>📥 Data Integration &amp; Reverse ETL</b></td>
      <td>
        <img src="https://img.shields.io/badge/Airbyte-6131F3?style=flat-square&logo=airbyte&logoColor=white" alt="Airbyte"/>
        <img src="https://img.shields.io/badge/Fivetran-326DE6?style=flat-square&logo=fivetran&logoColor=white" alt="Fivetran"/>
        <img src="https://img.shields.io/badge/dltHub-4285F4?style=flat-square&logo=python&logoColor=white" alt="dltHub"/>
        <img src="https://img.shields.io/badge/Hightouch-000000?style=flat-square&logo=hightouch&logoColor=white" alt="Hightouch"/>
      </td>
    </tr>
    <tr>
      <td><b>⚙️ Orchestration</b></td>
      <td>
        <img src="https://img.shields.io/badge/Apache_Airflow-017CEE?style=flat-square&logo=apache-airflow&logoColor=white" alt="Apache Airflow"/>
        <img src="https://img.shields.io/badge/Astronomer-4F46E5?style=flat-square&logo=apacheairflow&logoColor=white" alt="Astronomer"/>
        <img src="https://img.shields.io/badge/Prefect-070E10?style=flat-square&logo=prefect&logoColor=white" alt="Prefect"/>
        <img src="https://img.shields.io/badge/Mage-8A2BE2?style=flat-square&logo=magic&logoColor=white" alt="Mage"/>
        <img src="https://img.shields.io/badge/Dagster-251E3E?style=flat-square&logo=dagster&logoColor=white" alt="Dagster"/>
        <img src="https://img.shields.io/badge/Orchestra-000000?style=flat-square&logo=data%3Aimage%2Fsvg%2Bxml&logoColor=white" alt="Orchestra"/>
      </td>
    </tr>
    <tr>
      <td><b>📊 BI &amp; Analytics</b></td>
      <td>
        <img src="https://img.shields.io/badge/Mode-000000?style=flat-square&logo=mode&logoColor=white" alt="Mode"/>
        <img src="https://img.shields.io/badge/Hex-000000?style=flat-square&logo=hex&logoColor=white" alt="Hex"/>
        <img src="https://img.shields.io/badge/Power_BI-F2C811?style=flat-square&logo=powerbi&logoColor=black" alt="Power BI"/>
        <img src="https://img.shields.io/badge/Tableau-E97627?style=flat-square&logo=tableau&logoColor=white" alt="Tableau"/>
        <img src="https://img.shields.io/badge/Looker_Studio-4285F4?style=flat-square&logo=looker&logoColor=white" alt="Looker Studio"/>
        <img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=flat-square&logo=streamlit&logoColor=white" alt="Streamlit"/>
        <img src="https://img.shields.io/badge/Visivo-000000?style=flat-square&logo=data%3Aimage%2Fsvg%2Bxml&logoColor=white" alt="Visivo"/>
        <img src="https://img.shields.io/badge/Lightdash-000000?style=flat-square&logo=lightdash&logoColor=white" alt="Lightdash"/>
        <img src="https://img.shields.io/badge/Superset-0073B7?style=flat-square&logo=apache-superset&logoColor=white" alt="Superset"/>
        <img src="https://img.shields.io/badge/Metabase-509EE3?style=flat-square&logo=metabase&logoColor=white" alt="Metabase"/>
        <img src="https://img.shields.io/badge/Omni-EC1A58?style=flat-square" alt="Omni"/>
        <img src="https://img.shields.io/badge/Datadog-632CA6?style=flat-square&logo=datadog&logoColor=white" alt="Datadog"/>
      </td>
    </tr>
    <tr>
      <td><b>🚀 DevOps &amp; Cloud</b></td>
      <td>
        <img src="https://img.shields.io/badge/Terraform-7B42BC?style=flat-square&logo=terraform&logoColor=white" alt="Terraform"/>
        <img src="https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker"/>
        <img src="https://img.shields.io/badge/Kubernetes-326CE5?style=flat-square&logo=kubernetes&logoColor=white" alt="Kubernetes"/>
        <img src="https://img.shields.io/badge/Git-F05032?style=flat-square&logo=git&logoColor=white" alt="Git"/>
        <img src="https://img.shields.io/badge/GitHub_Actions-2088FF?style=flat-square&logo=github-actions&logoColor=white" alt="GitHub Actions"/>
        <img src="https://img.shields.io/badge/AWS-232F3E?style=flat-square&logo=amazonwebservices&logoColor=white" alt="AWS"/>
        <img src="https://img.shields.io/badge/Amazon_S3-569A31?style=flat-square&logo=amazons3&logoColor=white" alt="Amazon S3"/>
        <img src="https://img.shields.io/badge/Amazon_EC2-FF9900?style=flat-square&logo=amazonec2&logoColor=white" alt="Amazon EC2"/>
        <img src="https://img.shields.io/badge/AWS_Lambda-FF9900?style=flat-square&logo=awslambda&logoColor=white" alt="AWS Lambda"/>
        <img src="https://img.shields.io/badge/Step_Functions-CD2264?style=flat-square&logo=amazonaws&logoColor=white" alt="AWS Step Functions"/>
        <img src="https://img.shields.io/badge/GitLab-FC6D26?style=flat-square&logo=gitlab&logoColor=white" alt="GitLab"/>
        <img src="https://img.shields.io/badge/GCP-4285F4?style=flat-square&logo=google-cloud&logoColor=white" alt="GCP"/>
      </td>
    </tr>
    <tr>
      <td><b>🤖 AI Tooling</b></td>
      <td>
        <img src="https://img.shields.io/badge/Claude_Code-D97757?style=flat-square&logo=anthropic&logoColor=white" alt="Claude Code"/>
        <img src="https://img.shields.io/badge/Cursor-000000?style=flat-square&logo=cursor&logoColor=white" alt="Cursor"/>
        <img src="https://img.shields.io/badge/Codex-000000?style=flat-square&logo=openai&logoColor=white" alt="Codex"/>
        <img src="https://img.shields.io/badge/MCP_Servers-4B32C3?style=flat-square&logo=data%3Aimage%2Fsvg%2Bxml&logoColor=white" alt="MCP servers (dbt, Asana, Slack)"/>
      </td>
    </tr>
  </table>
</div>

## 📊 Stats <img src="https://user-images.githubusercontent.com/73097560/115834477-dbab4500-a447-11eb-908a-139a6edaec5c.gif">

### GitHub Stats

<div align="center">
  <table border="0" style="border-collapse: collapse; border: none;">
    <tr style="border: none;">
      <!-- Left: Contribution Cityscape (larger) -->
      <td width="58%" align="center" style="border: none; padding: 10px;" valign="middle">
        <img src="https://raw.githubusercontent.com/MarkPhamm/MarkPhamm/output/github-isometric-calendar.svg" width="560px" alt="Contribution Cityscape" />
      </td>
      <!-- Right: GitHub Stats on top, Top Languages below -->
      <td width="42%" align="center" style="border: none; padding: 10px;" valign="middle">
        <img src="https://github-readme-stats-fast.vercel.app/api?username=markphamm&theme=tokyonight&show_icons=true&include_all_commits=true&bg_color=0b0f19&title_color=88C0D0&text_color=e5e7eb&icon_color=88C0D0&border_color=1f2937&hide_border=false" width="380" alt="GitHub Stats" />
        <br /><br />
        <img src="https://github-readme-stats-fast.vercel.app/api/top-langs/?username=markphamm&layout=compact&theme=tokyonight&bg_color=0b0f19&title_color=88C0D0&text_color=e5e7eb&icon_color=88C0D0&border_color=1f2937&hide_border=false" width="380" alt="Top Languages" />
      </td>
    </tr>
  </table>
</div>

<img src="https://user-images.githubusercontent.com/73097560/115834477-dbab4500-a447-11eb-908a-139a6edaec5c.gif" width="100%" height="8px" alt="Line Divider" />

### Things I'm working on this week
<!--START_SECTION:waka-->

```txt
SQL                8 hrs 16 mins         ███████░░░░░░░░░░░░░░░░░░   28.12 %
Markdown           8 hrs 1 min           ██████▓░░░░░░░░░░░░░░░░░░   27.29 %
HTML               3 hrs 14 mins         ██▓░░░░░░░░░░░░░░░░░░░░░░   11.02 %
Text               2 hrs 29 mins         ██░░░░░░░░░░░░░░░░░░░░░░░   08.46 %
Python             1 hr 46 mins          █▓░░░░░░░░░░░░░░░░░░░░░░░   06.01 %
```

<!--END_SECTION:waka-->

<p align="center">
  <img src="./images/wakatime_activity.svg" alt="WakaTime Activity" />
</p>
