-- lifetime value = cumulative revenue until now per customer

with active_priced as (
    select
        fact_subs.customer_key,
        fact_subs.plan,
        plan.monthly_price,
        greatest(
            date_diff('month', fact_subs.sub_started_at, current_timestamp),
            0
        ) as tenure_months  -- 0 to avoid sub_started_at on future (mock data)

    from {{ ref('fact_subscriptions') }} as fact_subs
    join {{ ref('plan_pricing') }} as plan
        on plan.plan = fact_subs.plan
    where fact_subs.is_current
        and fact_subs.status = 'active'
)

select
    customer_key,
    count(*)                                as active_subscriptions,
    sum(monthly_price)                      as current_mrr,
    max(tenure_months)                      as tenure_months,
    sum(monthly_price * tenure_months)      as ltv_to_date
from active_priced
group by customer_key
order by ltv_to_date desc