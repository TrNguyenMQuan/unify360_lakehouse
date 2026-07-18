with source as (
    select * from {{ source('bronze', 'app_events') }}
),

ranked as (
    select *,
        row_number() over (partition by event_id order by _ingested_at desc) as rank
    from source
)

select
    event_id,
    event_type,
    anonymous_id,
    user_id,            -- null is okay because without login user dont have user id
    "timestamp"                                 as event_at,
    "properties.page"                           as page,
    "properties.referrer"                       as referrer,
    "context.device"                            as device,
    "context.app_version"                       as app_version,
    try_cast("properties.duration_s" as double) as duration_s,
    "properties.feature"                        as feature,
    from_iso8601_timestamp(_ingested_at)        as _ingested_at
from ranked
where rank = 1