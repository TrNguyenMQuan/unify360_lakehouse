with source as (
    select * from {{ source('bronze', 'app_subscriptions') }}
),

ranked as (
    select
        *,
        row_number() over(
            partition by subscription_id
            order by updated_at desc
        ) as rank
    from source
)

select
    subscription_id,
    account_id,
    plan,
    status,
    try_cast(started_at as timestamp(6) with time zone)     as sub_started_at,
    try_cast(updated_at as timestamp(6) with time zone)     as sub_updated_at,
    from_iso8601_timestamp(_ingested_at)                    as _ingested_at
from ranked
where rank = 1