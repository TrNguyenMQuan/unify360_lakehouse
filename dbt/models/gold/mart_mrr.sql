-- MRR: Monthly Recurring Revenue = total revenue monthly for subscriptions is active

with current_active as (
    select customer_key, subscription_id, plan
    from {{ ref('fact_subscriptions') }}
    where is_current
        and status = 'active'
),

priced as (
    select
        current_active.plan,
        plan.monthly_price
    from current_active
    join {{ ref('plan_pricing') }} as plan
        on plan.plan = current_active.plan
)

select
    plan,
    count(*)                as active_subscriptions,
    max(monthly_price)      as monthly_price,
    sum(monthly_price)      as mrr
from priced
group by plan
order by mrr desc