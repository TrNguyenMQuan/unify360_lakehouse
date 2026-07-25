-- 1 customer key only belong to 1 person
select
    customer_key,
    count(distinct email_hash) as n_people
from {{ ref('identity_map') }}
group by customer_key
having count(distinct email_hash) > 1