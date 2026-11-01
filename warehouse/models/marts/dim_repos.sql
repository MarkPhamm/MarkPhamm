select
    repo_name,
    stars,
    language,
    commits_this_year,
    status,
    pushed_at,
    url
from {{ ref('int_repo_health') }}
order by stars desc, repo_name
