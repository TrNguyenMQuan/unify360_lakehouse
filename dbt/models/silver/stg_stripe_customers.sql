-- conform included: cast, rename and normailize

with source as (
    select * from {{ source('bronze', 'stripe_customers') }}
),

cleaned as (
    select
        id                                                  as source_id,
        lower(trim(email))                                  as email_norm,
        to_hex(sha256(to_utf8(lower(trim(email)))))         as email_hash,
        "metadata.country"                                  as country,
        name                                                as full_name,
        created                                             as created_epoch,
        from_iso8601_timestamp(_ingested_at)                as _ingested_at
    from source
    where email is not null
        and trim(email) <> ''
),

final as (
    select
        'stripe'                                            as source_system,
        source_id,
        email_hash,
        split_part(email_norm, '@', 2)                      as email_domain,
        substr(email_norm, 1, 1) || '***@'
            || split_part(email_norm, '@', 2)               as email_masked,
        split_part(full_name, ' ', 1)                       as first_name,
        substr(split_part(full_name, ' ', 2), 1, 1)         as last_name_initial,
        cast(null as varchar)                               as company,
        country,
        cast(null as varchar)                               as account_id,
        cast(null as varchar)                               as lead_source,
        cast(null as varchar)                               as campaign,
        try_cast(from_unixtime(cast(created_epoch as bigint))   as timestamp(6) with time zone) as source_created_at,
        _ingested_at
    from cleaned
)

select * from final