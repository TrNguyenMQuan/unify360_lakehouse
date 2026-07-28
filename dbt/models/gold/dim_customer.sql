-- collapse all customer into 1 row/1 person even they have 1, 2 or 3 source system
with map as (
    select customer_key, source_system, source_id
    from {{ ref('identity_map') }}
),

attribute as (
    select
        m.customer_key,
        c.source_system,
        -- this use on case when 1 customer key have different attr at 3 source although by checking it doest has
        case c.source_system
            when 'app' then 3 when 'stripe' then 2 when 'crm' then 1
        end                     as source_priority,
        c.email_domain,
        c.email_masked,
        c.first_name,
        c.last_name_initial,
        c.company,
        c.country,
        c.account_id,
        c.lead_source,
        c.campaign,
        c.source_created_at
    from map as m
    join {{ ref('customers') }} as c
        on m.source_system = c.source_system
        and m.source_id = c.source_id
),

-- collapse into 1 row / 1 person
golden as (
    select
        customer_key,

        -- email_atrrs: 3 source must be have the same
        max(email_domain)                           as email_domain,
        max(email_masked)                           as email_masked,

        -- name_atrrs: it can has there difference between 3 source
        max_by(first_name, source_priority)         as first_name,
        max_by(last_name_initial, source_priority)   as last_name_initial,

        -- attrs only have in 1 source, max can ignore null
        max(company)                                as company,     -- crm
        max(country)                                as country,     -- stripe
        max(account_id)                             as account_id,   -- app
        max(lead_source)                            as lead_source, -- crm
        max(campaign)                               as campaign,    -- crm

        -- the first time have this person in any source
        min(source_created_at)                      as first_seen_at,

        -- which source have this person
        max(if(source_system = 'crm',   1, 0))      as in_crm,
        max(if(source_system = 'stripe', 1, 0))     as in_stripe,
        max(if(source_system = 'app',   1, 0))      as in_app,
        count(*)                                    as n_source_records
    from attribute
    group by customer_key
)

select * from golden