select
    name as repo_name,
    coalesce(stars, 0) as stars,
    language,
    pushed_at,
    created_at,
    description,
    url
from {{ source('github', 'repos') }}
where name is not null
