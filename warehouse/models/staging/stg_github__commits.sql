select
    day,
    coalesce(contributions, 0) as contributions
from {{ source('github', 'contributions') }}
where day is not null
