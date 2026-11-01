select
    day,
    language,
    seconds
from {{ source('wakatime', 'languages') }}
where language is not null
  and seconds > 0
