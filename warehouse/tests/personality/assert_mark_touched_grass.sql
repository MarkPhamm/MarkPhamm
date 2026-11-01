{{ config(tags=['personality'], severity='warn') }}

select
    day,
    contributions,
    coding_hours
from {{ ref('fct_contributions') }}
where day > current_date - 7
  and (
      coding_hours > 10
      or (coding_hours is null and contributions > 40)
  )
