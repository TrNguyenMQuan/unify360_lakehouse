-- conversion funnel lead -> signup -> paid

with customer_stage as (
    select
        customer.customer_key,
        customer.in_crm,
        customer.in_app,
        max(case
            when fact_subs.is_current and fact_subs.status = 'active' and fact_subs.plan <> 'free'
            then 1 else 0
            end) as is_paid

    from {{ ref('dim_customer') }} as customer
    left join {{ ref('fact_subscriptions') }} as fact_subs
        on customer.customer_key = fact_subs.customer_key
    group by customer.customer_key, customer.in_crm, customer.in_app
)

select
    count_if(in_crm = 1)                                    as leads,
    count_if(in_crm = 1 and in_app = 1)                     as signups,
    count_if(in_crm = 1 and in_app = 1 and is_paid = 1)     as paid,

    -- conversion rate
    round(1.0 * count_if(in_crm = 1 and in_app = 1)
            / nullif(count_if(in_crm = 1), 0), 3)           as lead_to_signup_rate,
    round(1.0 * count_if(in_crm = 1 and in_app = 1
        and is_paid = 1) / nullif(count_if(in_crm = 1
        and in_app = 1), 0), 3)                             as signup_to_paid_rate
from customer_stage
