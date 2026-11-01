select
    repo as repo_name,
    coalesce(commits, 0) as commits
from {{ source('github', 'repo_commits') }}
where repo is not null
