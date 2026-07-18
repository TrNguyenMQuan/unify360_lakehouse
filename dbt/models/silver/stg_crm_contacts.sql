-- Conform source from CRM inclued: asstype, rename, normalize

with source as (
    select * from {{ source('bronze', 'crm_contacts') }}
),

cleaned as(
    select
        lower(trim(contact_email))                          as email_norm,
        to_hex(sha256(to_utf8(lower(trim(contact_email))))) as email_hash,
        trim(first_name)                                    as first_name,
        trim(last_name)                                     as last_name,
        trim(company)                                       as company,
        lead_source,
        campaign,
        created_date                                        as source_created_date,
        from_iso8601_timestamp(_ingested_at)                as ingested_at
    from source
    where contact_email is not null
        and trim(contact_email) <> ''
),

final as (
    select
        'crm'                                   as source_system,
        email_hash                              as source_id,
        email_hash                              as email_hash,     -- key join
        split_part(email_norm, '@', 2)          as email_domain,
        substr(email_norm, 1, 1) || '***@'
            || split_part(email_norm, '@', 2)   as email_masked,
        first_name,
        substr(last_name, 1, 1)                 as last_name_initial,
        company,
        -- pad null to 3 another stg can union
        cast(null as varchar)                   as country,
        cast(null as varchar)                   as account_id,
        lead_source,
        campaign,
        try_cast(source_created_date as timestamp(6) with time zone) as source_created_at,
        ingested_at                             as _ingested_at
    from cleaned
)

select * from final