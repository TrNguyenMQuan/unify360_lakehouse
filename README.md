# Unify360 — Multi-Source Customer 360 Lakehouse

> A **metadata-driven** data platform that ingests from **four heterogeneous sources** (billing API, CRM files, an application database, and NoSQL event logs), unifies them into a single **Customer 360** view, and serves analytics from an open **lakehouse** — built with **DataOps** practices (data quality, reconciliation, monitoring, CI/CD, PII masking).

**Status:** 🚧 In development &nbsp;·&nbsp; **Stack:** Python · Iceberg · MinIO · Trino · Airflow · dbt · Soda · Prometheus/Grafana · Metabase · Docker

> _Personal Data Engineering portfolio project. Docs are in English; internal working notes (`docs/ROADMAP.md`) are in Vietnamese._

---

## Table of contents
- [Why this project](#why-this-project)
- [Architecture](#architecture)
- [Data sources](#data-sources)
- [The metadata-driven ingestion framework](#the-metadata-driven-ingestion-framework)
- [Medallion layers](#medallion-layers)
- [Identity resolution → Customer 360](#identity-resolution--customer-360)
- [Tech stack](#tech-stack)
- [Repository structure](#repository-structure)
- [Getting started](#getting-started)
- [DataOps](#dataops)
- [Skills demonstrated](#skills-demonstrated)
- [Roadmap](#roadmap)

---

## Why this project

In a typical SaaS company the **same customer is scattered across systems**: Marketing knows them in the **CRM**, Product in the **app database**, Finance in **Stripe**, and their behavior lives in **event logs**. No single system can answer:

> *"What is this customer's lifetime value, and how long did they take to convert from lead → signup → paid?"*

Unify360 tackles the core Data Engineering problem: **ingest heterogeneous sources and integrate them into one trustworthy, analytics-ready model** — the foundation of every modern data team.

## Architecture

```
4 SOURCES (4 types)          INGESTION FRAMEWORK (metadata-driven)      LAKEHOUSE (Iceberg on MinIO)
Stripe API ─┐               ┌──────────────────────────────┐
CRM CSV ────┤── read CONFIG►│  Generic Ingestion Engine      │── BRONZE  raw, per source
App Postgres┤   (metadata   │   ├ RestConnector              │── SILVER  clean · conform · dedupe ·
Mongo events┘    table/YAML)│   ├ CsvConnector               │           PII mask · IDENTITY RESOLUTION
                            │   ├ JdbcConnector              │── GOLD    Customer 360: dim_customer ·
  "+ source = + 1 row"      │   └ MongoConnector             │           MRR/churn · funnel · LTV · recon
                            └──────────────────────────────┘
        Airflow (DAG orchestration & lineage) · dbt (conform & integrate) · Trino (query on lake) · Metabase (BI)
        DataOps: Soda (DQ) · schema evolution · CI/CD (GitHub Actions) · Prometheus/Grafana · runbook
```

The lakehouse is a **true lakehouse**: analytics run **directly on Iceberg tables in object storage via Trino** — no copy into a separate warehouse.

## Data sources

| Type | Source | Entities | How it's provided |
|---|---|---|---|
| **REST API** | Stripe (test mode) | customers, subscriptions, invoices | free test API + seed generator |
| **CSV / files** | CRM export | contacts, campaign, lead_source | generated (Faker) |
| **Relational DB** | Postgres (app OLTP) | users, accounts, plans, signup | seeded |
| **NoSQL** | MongoDB | product events (page_view, click, session) | generated JSON |

> Sources are **simulated with reproducible generators** — anyone can clone and run, and **faults can be injected** (schema drift, bad rows) to demonstrate incident handling.

## The metadata-driven ingestion framework

Instead of writing one pipeline per source, a single **config table** describes every source, and a **generic engine** dispatches to the correct connector by `type`. **Adding a new source = adding one config row** — no new pipeline code.

```
source_name      | type     | load_mode   | watermark   | primary_key | target_bronze
-----------------+----------+-------------+-------------+-------------+------------------------
stripe_customers | rest_api | incremental | created     | id          | bronze.stripe_customers
crm_contacts     | csv      | full        | -           | email       | bronze.crm_contacts
app_users        | jdbc     | incremental | updated_at  | user_id     | bronze.app_users
app_events       | mongodb  | incremental | event_ts    | event_id    | bronze.app_events
```

Connectors implement a common interface (`extract() → DataFrame/records`), so the engine treats every source uniformly: read config → pick connector → apply `load_mode` (full / incremental via `watermark`) → land to Bronze idempotently (upsert on `primary_key`).

## Medallion layers

| Layer | Tables | Purpose |
|---|---|---|
| **Bronze** | `stripe_*`, `crm_*`, `app_*`, `events_*` | raw per source, append-only, schema-on-read |
| **Silver** | `customers` (PII masked), `subscriptions`, `events`, **`identity_map`** | cleaned · conformed schema · deduped · **identity resolved** · validated (Soda) |
| **Gold** | `dim_customer` (360), `fct_subscriptions` (SCD-2), `mart_mrr`, `mart_funnel`, `mart_ltv`, `recon_billing_vs_app` | analytics-ready |

## Identity resolution → Customer 360

The same person appears in all four sources under **different keys**:

```
stripe_customer_id  ↔  crm_email  ↔  app_user_id  ↔  event_anonymous_id
```

- **`identity_map`** (Silver) links these keys into one canonical `customer_key`.
- **`dim_customer`** (Gold) is the unified 360 view.
- **`fct_subscriptions`** applies **SCD type-2** to track plan changes over time.
- **`recon_billing_vs_app`** reconciles revenue (Stripe) against active subscriptions (app DB) and raises an alert on mismatch.

## Tech stack

| Layer | Tool |
|---|---|
| Ingestion framework | Python connectors + config table (optional: dlt) |
| Object storage | MinIO (S3-compatible) |
| Table format | Apache Iceberg |
| Catalog | Project Nessie / Iceberg REST |
| Query engine | Trino |
| Orchestration | Airflow (DAG-based) |
| Transform | dbt (dbt-trino) |
| Data quality | Soda Core |
| Monitoring | Prometheus + Grafana |
| BI | Metabase |
| CI/CD | GitHub Actions |
| Containers | Docker Compose |

## Repository structure

```
unify360/
├── ingestion/                # metadata-driven framework
│   ├── engine.py             #   generic engine (reads config → dispatch)
│   ├── connectors/           #   rest.py · csv.py · jdbc.py · mongo.py
│   └── config/sources.yml    #   source registry (the "config table")
├── generators/               # source simulators (Stripe/CRM/Postgres/Mongo seeders)
├── dbt_unify360/             # dbt project: staging · silver · gold
│   └── models/  bronze/ · silver/ · gold/
├── airflow/                  # Airflow DAGs + schedules (dags/ · plugins/)
├── data_quality/             # Soda checks (YAML)
├── monitoring/               # Prometheus + Grafana config
├── docs/
│   ├── ROADMAP.md            # milestone checklist (progress source of truth)
│   ├── architecture.png      # diagram
│   └── runbook.md            # incident handling
├── docker-compose.yml        # MinIO · Postgres · Mongo · Nessie · Trino · Airflow · Metabase · Prom/Grafana
├── .github/workflows/ci.yml  # lint + test + dbt parse
└── .env(.example)
```

## Getting started

```bash
cp .env.example .env                 # fill in secrets
docker compose up -d                 # bring up the full stack

# 1) generate source data
python -m generators.seed_all

# 2) run ingestion (config-driven) → Bronze
python -m ingestion.engine --all

# 3) transform Bronze → Silver → Gold
cd dbt_unify360 && dbt build

# 4) query the lakehouse
#    Trino:    http://localhost:8080
#    Metabase: http://localhost:3000  → dashboard "Customer 360"
```

## DataOps

- **Data quality:** Soda checks on Silver/Gold (not-null keys, referential integrity, freshness).
- **Reconciliation:** stream/source totals vs derived tables (`recon_billing_vs_app`).
- **Monitoring:** Prometheus + Grafana (ingestion duration, row counts, DQ pass rate, freshness SLAs) with alerts.
- **CI/CD:** GitHub Actions — lint (ruff/black), unit tests, `dbt parse`.
- **Security:** PII masking in Silver; secrets via `.env` / Docker secrets (never committed).
- **Incident handling:** `docs/runbook.md` + a demo that injects bad data → Soda fails → alert fires → documented fix.

## Skills demonstrated

- Metadata-driven ingestion framework (config-driven, connector pattern, incremental + idempotent).
- Cross-source **identity resolution** and **Customer 360** modeling (SCD-2, reconciliation).
- **True lakehouse** on object storage (Iceberg + Trino), queried without a separate warehouse.
- DAG-based orchestration & lineage (Airflow), analytics engineering (dbt).
- **DataOps**: data quality gates, monitoring/alerting, CI/CD, PII masking, incident runbook.

## Roadmap

Milestone-by-milestone plan and progress: [`docs/ROADMAP.md`](docs/ROADMAP.md).
