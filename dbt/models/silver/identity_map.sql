-- create customer_key by email_hash
-- table included: have many account with 1 source system, have 1 account on 1/2/3 source_system
with source_keys as (
    -- email_hash = key match deterministic (same email hash = same person)
    select
        source_system,
        source_id,
        email_hash
    from {{ ref('customers') }}
),

resolved as (
    select
        source_system,
        source_id,
        email_hash,
        -- customer_key = surrograte key = hash(email_hash) if use dense_rank when add new person it will create new key
        to_hex(sha256(to_utf8(email_hash)))  as customer_key
    from source_keys
)

select
    customer_key,
    source_system,
    source_id,
    email_hash
from resolved