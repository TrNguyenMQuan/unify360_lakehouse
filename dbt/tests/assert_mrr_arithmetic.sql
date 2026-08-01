select plan, active_subscriptions, monthly_price, mrr
from {{ ref('mart_mrr') }}
where mrr <> active_subscriptions * monthly_price