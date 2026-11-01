<p align="center"><img src="terrace/terrace.svg" width="100%" alt="Ruộng Commit: a hillside of 12 rice terraces in Mù Cang Chải, one per month from December 2025 to November 2026, ripening from green to gold with MarkPhamm's GitHub contributions. A thatched stilt house sits on the hilltop, four koi swim in the paddy below, no farmers are out planting yet, and the sky shows night in Hanoi."/></p>

<p align="center"><sub>Ruộng Commit: rice terraces in the hills of Mù Cang Chải that grow with my GitHub activity, 4,427 contributions in the last year. Each terrace is a month, and the rice ripens from green to gold as the commits come in, so March is the ripest and November was just planted. Four koi swim in the paddy, one for each repo with at least 10 stars: <a href="https://github.com/MarkPhamm/dbt-Fundamental">dbt-Fundamental</a> (37 stars), <a href="https://github.com/MarkPhamm/local_streaming_pipeline">local_streaming_pipeline</a> (22), <a href="https://github.com/MarkPhamm/skytrax_reviews">skytrax_reviews</a> (13) and <a href="https://github.com/MarkPhamm/local_warehouse_pipeline">local_warehouse_pipeline</a> (11). No one has planted a seedling in the last 30 days, so the terraces are waiting for their first farmer. Nobody has fed the koi yet today, so they are circling hopefully. The sky follows the time in Hanoi, where it's night right now.</sub></p>

<p align="center">
  <a href="https://github.com/MarkPhamm/MarkPhamm/issues/new?title=terrace%3A%20plant&amp;body=Just%20hit%20%2A%2ACreate%2A%2A.%20A%20farmer%20in%20a%20n%C3%B3n%20l%C3%A1%20will%20join%20the%20terraces%20on%20github.com/MarkPhamm%20in%20about%20a%20minute.%0A%0AEach%20visitor%20gets%20one%20farm%20chore%20a%20day%2C%20Hanoi%20time."><img src="https://img.shields.io/badge/Plant_a_seedling-3f7d4f?style=for-the-badge" alt="Plant a seedling"/></a>
  <a href="https://github.com/MarkPhamm/MarkPhamm/issues/new?title=terrace%3A%20feed&amp;body=Just%20hit%20%2A%2ACreate%2A%2A.%20A%20handful%20of%20food%20will%20land%20in%20the%20koi%20paddy%20on%20github.com/MarkPhamm%20in%20about%20a%20minute.%0A%0AEach%20visitor%20gets%20one%20farm%20chore%20a%20day%2C%20Hanoi%20time."><img src="https://img.shields.io/badge/Feed_the_koi-d9822b?style=for-the-badge" alt="Feed the koi"/></a>
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
</details>
