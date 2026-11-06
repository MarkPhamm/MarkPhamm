<p align="center"><img src="street/street.svg" width="100%" alt="Phố Commit, an illustrated street in Hanoi&#x27;s Old Quarter at night: tube houses named after my most active public repositories, motorbikes carrying my latest merged pull requests, and a phở cart serving my latest Substack post"/></p>

Phố Commit is a street in Hanoi's Old Quarter that grows with my GitHub activity: 4,406 contributions in the last year. Each tube house is one of my repos, and the busier I am in it, the taller it gets: `quickdbd-cli` is 6 floors after 215 commits this year. I haven't merged a pull request yet this year, so the road is quiet for now. The phở cart is serving my latest post from The Analytics Engineer's Handbook, [I let a coding agent build my dashboard. I didn't let it touch the math.](https://markphammm.substack.com/p/i-let-a-coding-agent-build-my-dashboard), and is waiting for its first order. Nobody has parked here this month yet, so the best spot on the sidewalk is yours. The sky follows the time in Hanoi, where it's night right now.

<p align="center">
  <a href="https://github.com/MarkPhamm/MarkPhamm/issues/new?title=street%3A%20park&amp;body=Just%20hit%20Create.%20Your%20motorbike%20gets%20parked%20on%20Ph%E1%BB%91%20Commit%20with%20your%20username%20on%20the%20ticket%2C%20and%20it%20stays%20for%2030%20days.%20One%20visit%20per%20person%20per%20day%2C%20Hanoi%20time."><img src="https://img.shields.io/badge/Park_a_motorbike-b3261e?style=for-the-badge" alt="Park a motorbike"/></a>
  <a href="https://github.com/MarkPhamm/MarkPhamm/issues/new?title=street%3A%20pho&amp;body=Just%20hit%20Create.%20The%20cart%20serves%20you%20a%20bowl%20of%20ph%E1%BB%9F%20and%20the%20bowl%20counter%20on%20the%20street%20goes%20up%20by%20one.%20One%20visit%20per%20person%20per%20day%2C%20Hanoi%20time."><img src="https://img.shields.io/badge/Order_ph%E1%BB%9F-2f7d5b?style=for-the-badge" alt="Order phở"/></a>
</p>
<p align="center"><sub>Buttons open a pre-filled issue. Hit Create and the street updates in about a minute.</sub></p>

<details>
<summary>How Phố Commit works</summary>

- **Houses** are my 8 public repositories with the most commits this calendar year, from the GitHub GraphQL API. The red sign is the repo name and the blue house number is its commit count.
- **Floors** go up at 10, 25, 50, 100 and 200 commits, so a quiet repo still gets a one-storey house and the busiest ones top out at six.
- **Motorbikes** on the road are my most recently merged pull requests in public repos this year, with the PR number on the plate.
- **The phở cart** serves the newest post from The Analytics Engineer's Handbook, read from its RSS feed. Every "Order phở" issue adds a bowl to the counter.
- **Parked bikes** belong to visitors who opened a "Park a motorbike" issue in the last 30 days. Everyone gets one visit per day, Hanoi time.
- **The sky** follows the time in Hanoi: dawn, day, dusk or night. After dark the windows and lanterns light up.
- **No server.** A GitHub Action redraws the street four times a day and right after each visit, then commits one SVG to this repo. The code is in [`street/`](street).

</details>
