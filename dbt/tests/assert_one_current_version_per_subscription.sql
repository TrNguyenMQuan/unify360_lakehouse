-- each subscription only have 1 version active
select subscription_id, count(*) as n_current
from {{ ref('fact_subscriptions') }}
where is_current
group by subscription_id
having count(*) <> 1