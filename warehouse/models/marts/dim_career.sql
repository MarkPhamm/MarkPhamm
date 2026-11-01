select
    company,
    role,
    start_date,
    end_date,
    end_date is null as is_current,
    date_diff('month', start_date, coalesce(end_date + 1, current_date)) as months,
    url
from {{ ref('stg_career__roles') }}
order by start_date, company
