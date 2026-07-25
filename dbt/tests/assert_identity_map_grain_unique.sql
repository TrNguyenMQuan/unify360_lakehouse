-- each person come from a (source system and source id) unique
select
    source_system,
    source_id,
    count(*) as n
from {{ ref('identity_map') }}
group by source_system, source_id
having count(*) > 1