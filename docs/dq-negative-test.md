# Data Quality Negative Test — Evidence

**Date:** 2026-08-04 · **Milestone:** M8 · **Layer under test:** Bronze (5 tables, 31 Soda checks)

## Why this test exists

Writing 58 data-quality checks proves nothing on its own. A check that never fires is
indistinguishable from a check that *cannot* fire — a typo in a threshold, a query pointing at
the wrong table, or a condition that is structurally impossible all produce the same green
dashboard.

This test injects known defects and asserts that **the predicted check fails, at the predicted
value**. Failing *somewhere* is not enough: if a defect trips a different check than expected,
the check is measuring something other than what its name claims.

## Method: branch-isolated sandbox

Injecting bad data into a working lakehouse is a bad idea — rollback is manual, error-prone, and
a mistake leaves production data dirty.

Instead the test runs on a **Nessie branch**. Nessie is the catalog, so a branch is a pointer to a
catalog commit: creating one copies **zero bytes**. Writes on the branch produce new Iceberg
metadata that only the branch points to; `main` keeps pointing at the old metadata and is
physically unchanged. Rollback is a single API call that deletes the pointer.

Trino's Iceberg connector does not support `table@branch` syntax — the Nessie ref is fixed per
catalog. A second catalog (`iceberg_dq`) pinned to `ref=dq_sandbox` is therefore required. This
is also what makes the isolation airtight: the injection commands physically cannot address
`main`, because the catalog they run through does not know it exists.

| | Catalog | Nessie ref |
|---|---|---|
| Production | `iceberg` | `main` |
| Sandbox | `iceberg_dq` | `dq_sandbox` |

Both catalogs read the same MinIO bucket and share every pre-existing data file.

## Setup

```bash
make dq-branch      # create Nessie branch dq_sandbox from main
make dq-scan        # baseline on the branch
```

Baseline: **31/31 checks PASSED** — identical to `main`. The branch has not diverged yet, so both
refs resolve to the same files. Establishing this baseline is what makes later failures
attributable: without it, a red check could have been red all along.

## Injections and results

Each injection targets one Soda check and one data-quality dimension. Predictions were written
**before** running the scan.

| # | Injection | Dimension | Predicted failure | Actual |
|---|---|---|---|---|
| 1 | 3 rows with `contact_email = NULL` | Completeness | `missing_count(contact_email) = 0` -> 3 | `check_value: 3` |
| 2 | 5 existing rows duplicated | Consistency | `duplicate_count(contact_email) = 0` -> 5 | `check_value: 5` |
| 3 | `ALTER TABLE ... DROP COLUMN company` | Schema | `Schema Check` + `column_count = 10` -> 9 | both failed |

Cumulative scan results after each step: **1 -> 2 -> 4 failures** out of 31 checks. No unexpected
check fired, and no expected check stayed silent.

### Raw evidence — sandbox after all three injections

```
Scan summary:
27/31 checks PASSED:
    crm_contacts in bronze_dq
    stripe_customers in bronze_dq
    app_users in bronze_dq
    app_subscriptions in bronze_dq
    app_events in bronze_dq
4/31 checks FAILED:
    crm_contacts in bronze_dq
      Schema Check [FAILED]
        fail_missing_column_names = [company]
        schema_measured = [contact_email varchar, first_name varchar, last_name varchar,
                           lead_source varchar, campaign varchar, created_date varchar,
                           industry varchar, _source varchar, _ingested_at varchar]
      column_count = 10 [FAILED]
        check_value: 9.0
      missing_count(contact_email) = 0 [FAILED]
        check_value: 3
      duplicate_count(contact_email) = 0 [FAILED]
        check_value: 5
Oops! 4 failures. 0 warnings. 0 errors. 27 pass.
```

### Raw evidence — `main`, scanned at the same moment

```
All is good. No failures. No warnings. No errors.
```

Table state at that instant:

| | `main` | `dq_sandbox` |
|---|---|---|
| Nessie hash | `eaa78f3f63d30ca7` | `0aab20586868fc32` |
| `crm_contacts` rows | 501 | 509 |
| NULL emails | 0 | 3 |
| Columns | 10 | 9 |

Same checks, same MinIO bucket, same underlying Parquet files — four failures on one ref, zero on
the other. This is the isolation proof.

## Incidental finding: checks that silently tested the wrong environment

Running the same checks against a second environment exposed a latent defect. Seven custom SQL
checks in `bronze_checks.yml` hardcoded the catalog:

```yaml
hours_since_ingest query: |
  SELECT ... FROM iceberg.bronze.crm_contacts     # always reads main
```

Whatever data source Soda connected to, these queries read `iceberg` — that is, `main`. Had this
gone unnoticed, the sandbox scan would have reported green while defects sat in the branch: a test
passing because it inspected the wrong object.

Fixed by removing the catalog prefix so table names resolve against the connection's
catalog/schema. A check should describe **what** is correct, not **where** it lives — "where" is
the connection's job.

## Rollback

```bash
make dq-clean       # DELETE /api/v2/trees/dq_sandbox@<hash>
make dq-branches    # only `main` remains
make verify         # green, as if nothing happened
```

Deleting the branch leaves the injected data files unreferenced on MinIO — harmless orphans,
invisible to Trino, reclaimed by Iceberg orphan-file cleanup.

## Reproduce

```bash
make dq-branch
make dq-scan                              # 31/31 PASS  (baseline)
make dq-inject-null  && make dq-scan      # 1 failure
make dq-inject-dup   && make dq-scan      # 2 failures
make dq-inject-drop  && make dq-scan      # 4 failures
make scan-bronze                          # main: still 31/31 PASS
make dq-clean
```

`dq-inject-drop` must run last — the two INSERT statements reference the `company` column.

## What this validates

- The Bronze quality gate detects completeness, consistency, and schema defects, and reports the
  correct magnitude for each.
- Severity levels are meaningful: these injections produce `FAIL` (blocking), distinct from the
  structural `WARN` conditions the same suite emits in normal operation.
- Destructive quality experiments can run against real lakehouse data with a guaranteed,
  single-command rollback — the capability that justifies Nessie as the catalog rather than a
  plain metastore.
