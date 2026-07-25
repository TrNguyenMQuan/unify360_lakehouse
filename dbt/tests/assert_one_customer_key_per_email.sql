-- each email_hash can just create 1 customer_key
select
    email_hash
from {{ ref('identity_map') }}
group by email_hash
having count(distinct customer_key) > 1