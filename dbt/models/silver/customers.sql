-- Sivler customers: union 4 source into 1 schema

with unioned as (
    -- use union because each stg is difference by source_system and source_id
    select * from {{ ref('stg_crm_contacts') }}
    union all
    select * from {{ ref('stg_stripe_customers') }}
    union all
    select * from {{ ref('stg_app_users') }}
),

ranked as (
    select
        *,
        row_number() over (
            partition by source_system, source_id
            order by _ingested_at desc
        ) as rank
    from unioned
)

-- Trino dont has select except
select
    source_system,
    source_id,
    email_hash,
    email_domain,
    email_masked,
    first_name,
    last_name_initial,
    company,
    country,
    account_id,
    lead_source,
    campaign,
    source_created_at,
    _ingested_at
from ranked
where rank = 1