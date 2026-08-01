-- constraint: leads >= signup >= paid
select leads, signups, paid
from {{ ref('mart_funnel') }}
where signups > leads or paid > signups