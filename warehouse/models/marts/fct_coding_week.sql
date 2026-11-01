with week as (
    select
        language,
        sum(seconds) as seconds
    from {{ ref('stg_wakatime__sessions') }}
    where day is null
       or day > current_date - 7
    group by language
)

select
    language,
    round(seconds / 3600, 2) as hours,
    round(100 * seconds / sum(seconds) over (), 2) as share_pct
from week
order by seconds desc, language
