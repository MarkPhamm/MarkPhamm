select
    company,
    role,
    start_date,
    end_date,
    url
from {{ ref('career_roles') }}
