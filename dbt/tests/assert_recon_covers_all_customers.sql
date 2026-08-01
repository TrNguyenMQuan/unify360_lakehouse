-- total of this table must to be equal total of dim customer
with recon as (select sum(n_customers) as n from {{ ref('recon_billing_vs_app') }}),
     dim   as (select count(*)         as n from {{ ref('dim_customer') }})

select recon.n as recon_total, dim.n as dim_total
from recon cross join dim  -- create 1 table without join key
where recon.n <> dim.n
