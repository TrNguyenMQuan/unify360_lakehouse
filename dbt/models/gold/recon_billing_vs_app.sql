-- recon coverage stripe (billing) vs app (subscription active)

with base as (
    select
        customer.customer_key,
        customer.in_stripe,
        max(case
                when fact_subs.is_current and fact_subs.status = 'active' and fact_subs.plan <> 'free'
                then 1 else 0
            end)    as has_active_paid      -- sub paid is run ?

    from {{ ref('dim_customer')}} as customer
    left join {{ ref('fact_subscriptions') }} as fact_subs
        on customer.customer_key = fact_subs.customer_key
    group by customer.customer_key, customer.in_stripe
)

select
    case
        when in_stripe = 1 and has_active_paid = 1 then '1_matched (billed + active)'
        when in_stripe = 1 and has_active_paid = 0 then '2_stripe_only (billed, no active sub)'
        when in_stripe = 0 and has_active_paid = 1 then '3_app_only (active sub, not billed)'
        else '4_neither'
    end             as recon_status,
    count(*)        as n_customers
from base
group by 1
order by recon_status