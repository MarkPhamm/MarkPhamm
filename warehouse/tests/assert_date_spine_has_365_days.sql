select count(*) as days
from {{ ref('fct_contributions') }}
having count(*) != 365
