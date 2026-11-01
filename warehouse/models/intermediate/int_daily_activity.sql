with spine as (
    select cast(range as date) as day
    from range(current_date - interval 364 day, current_date + interval 1 day, interval 1 day)
),

contributions as (
    select day, contributions
    from {{ ref('stg_github__commits') }}
),

coding as (
    select day, sum(seconds) as coding_seconds
    from {{ ref('stg_wakatime__sessions') }}
    where day is not null
    group by day
),

tracked as (
    select min(day) as first_tracked_day
    from coding
)

select
    spine.day,
    coalesce(contributions.contributions, 0) as contributions,
    case
        when spine.day >= tracked.first_tracked_day then coalesce(coding.coding_seconds, 0)
    end as coding_seconds
from spine
cross join tracked
left join contributions on contributions.day = spine.day
left join coding on coding.day = spine.day
