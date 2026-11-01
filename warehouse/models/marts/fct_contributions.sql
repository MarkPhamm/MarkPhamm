select
    day,
    contributions,
    round(coding_seconds / 3600, 2) as coding_hours,
    isodow(day) in (6, 7) as is_weekend
from {{ ref('int_daily_activity') }}
order by day
