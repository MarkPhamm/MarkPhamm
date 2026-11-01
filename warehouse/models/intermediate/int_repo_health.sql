with repos as (
    select * from {{ ref('stg_github__repos') }}
),

commits as (
    select * from {{ ref('stg_github__repo_commits') }}
),

joined as (
    select
        repos.repo_name,
        repos.stars,
        repos.language,
        repos.description,
        repos.url,
        repos.pushed_at,
        repos.created_at,
        coalesce(commits.commits, 0) as commits_this_year,
        date_diff('day', cast(repos.pushed_at as date), current_date) as days_since_push
    from repos
    left join commits on commits.repo_name = repos.repo_name
)

select
    *,
    case
        when days_since_push <= 120 then 'active'
        when days_since_push <= 730 then 'maintained'
        else 'dormant'
    end as status
from joined
