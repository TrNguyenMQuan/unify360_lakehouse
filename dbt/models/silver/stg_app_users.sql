with source as (
    select * from {{ source('bronze', 'app_users') }}
),

cleaned as (
    select
        user_id                                         as source_id,
        lower(trim(email))                              as email_norm,
        to_hex(sha256(to_utf8(lower(trim(email)))))     as email_hash,
        trim(first_name)                                as first_name,
        trim(last_name)                                 as last_name,
        country,
        created_at,
        account_id,
        from_iso8601_timestamp(_ingested_at)             as _ingested_at

    from source
    where email is not null
        and trim(email) <> ''
),

final as (
    select
        'app'                   as source_system,
        source_id,
        email_hash,
        split_part(email_norm, '@', 2)      as email_domain,
        substr(email_norm, 1, 1) || '***@'
            || split_part(email_norm, '@', 2)   as email_masked,
        first_name,
        substr(last_name, 1, 1)                 as last_name_initial,
        cast(null as varchar)                   as company,
        country,
        account_id,
        cast(null as varchar)                   as lead_source,
        cast(null as varchar)                   as campaign,
        try_cast(created_at as timestamp(6) with time zone) as source_created_at,
        _ingested_at
    from cleaned
)

select * from final