-- SCD-2 engine for subscriptions, dbt automatic manage valid_from/valid_to

{% snapshot scd_subscriptions %}

{# valid_from: real day change it not just at the momment snapshot #}
{{
    config(
        target_schema = 'snapshots',
        unique_key    = 'subscription_id',
        strategy      = 'timestamp',
        updated_at    = 'sub_updated_at'
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