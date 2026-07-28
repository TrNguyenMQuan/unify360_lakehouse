-- grain: 1 row / (subscription, version) - read snapshot + bridge customer + rename column in scd-2
with scd as (
    select * from {{ ref('scd_subscriptions') }}
),

fact as (
    select
        scd.dbt_scd_id                      as subscription_version_key,
        scd.subscription_id,
        customer.customer_key,
        scd.account_id,
        scd.plan,
        scd.status,
        scd.sub_started_at,
        scd.dbt_valid_from                  as valid_from,
        scd.dbt_valid_to                    as valid_to,
        scd.dbt_valid_to is null            as is_current

    from scd
    left join {{ ref('dim_customer') }} as customer
        on scd.account_id = customer.account_id
)

select * from fact 