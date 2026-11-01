{{ config(tags=['personality'], severity='error') }}

select
    language,
    share_pct
from {{ ref('fct_coding_week') }}
where language = 'SQL'
  and share_pct > 25
