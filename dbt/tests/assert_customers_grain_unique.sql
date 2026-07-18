-- Singular test: (source_system, source_id) is unique

select
    source_system,
    source_id,
    count(*) as n
from {{ ref('customers') }}
group by source_system, source_id
having count(*) > 1