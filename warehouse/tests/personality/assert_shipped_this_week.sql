{{ config(tags=['personality'], severity='error') }}

select coalesce(sum(contributions), 0) as contributions_last_7_days
from {{ ref('fct_contributions') }}
where day > current_date - 7
having coalesce(sum(contributions), 0) = 0
