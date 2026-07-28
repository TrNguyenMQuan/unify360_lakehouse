-- SCD-2 engine for subscriptions, dbt automatic manage valid_from/valid_to

{% snapshot scd_subscriptions %}

{{
    config(
        target_schema = 'snapshots',
        unique_key    = 'subscription_id',
        strategy      = 'check',                
        check_cols    = ['plan', 'status']
    )
}}

-- source of snapshot
select
    subscription_id,
    account_id,
    plan,
    status,
    sub_started_at,
    sub_updated_at
from {{ ref('subscriptions') }}

{% endsnapshot %}