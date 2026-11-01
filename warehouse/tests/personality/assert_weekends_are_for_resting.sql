{{ config(tags=['personality'], severity='warn') }}

with last_saturday as (
    select max(day) as saturday
    from {{ ref('fct_contributions') }}
    where isodow(day) = 6
)

select
    day,
    contributions
from {{ ref('fct_contributions') }}
cross join last_saturday
where day between saturday and saturday + 1
  and contributions > 0
