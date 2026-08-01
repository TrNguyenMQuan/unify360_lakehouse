# Engine metadata-driven: depend on config to chose connector with full and watermark load
from __future__ import annotations
import argparse
import yaml
import pandas as pd
import pyarrow as pa    # Iceberg write from arrow table
from ingestion.connectors.base import Connector
from ingestion.connectors.csv import CsvConnector
from ingestion.connectors.rest import RestConnector
from ingestion.connectors.jdbc import JdbcConnector
from ingestion.connectors.mongo import MongoConnector
from ingestion.catalog import get_catalog
from pyiceberg.exceptions import NoSuchTableError # iceberg table property

CONFIG_PATH = "ingestion/config/sources.yml"
WATERMARK_PROP = "unify360.watermark"

CONNECTORS: dict[str, type[Connector]] = {
    "csv": CsvConnector,
    "rest": RestConnector,
    "jdbc": JdbcConnector,
    "mongodb": MongoConnector
}

def load_config() -> dict:
    with open(CONFIG_PATH) as file:
        return yaml.safe_load(file)["sources"]

# pyiceberg write from pyarrow not directly with pandas
def to_bronze_arrow(df: pd.DataFrame) -> pa.Table:
    # convert_dtypes: int + null -> int64 nullable
    return pa.Table.from_pandas(
        df.convert_dtypes().astype("string"), preserve_index=False
    )  # one bug define user_id in table events is float but source_id in customer is int

def read_watermark(catalog, identifier: str) -> str | None:
    try:
        tbl = catalog.load_table(identifier)
    except NoSuchTableError:
        return None
    return tbl.properties.get(WATERMARK_PROP)

def ingest_by_connector(name: str, cfg: dict, catalog) -> None:
    conn_type = cfg["type"]
    if conn_type not in CONNECTORS:
        raise ValueError(f"Unknown type '{conn_type}'")

    connector: Connector = CONNECTORS[conn_type](cfg)
    mode = cfg.get("load_mode", "full")
    identifier = cfg["target_bronze"]

    since = read_watermark(catalog, identifier) if mode == "incremental" else None
    df = connector.extract(since=since)
    if df.empty:
        print(f"{name}: no have new records")
        return

    # calculate watermark before astype
    new_wm = str(df[cfg["watermark"]].max()) if mode == "incremental" else None

    df["_source"] = name
    df["_ingested_at"] = pd.Timestamp.now(tz="UTC").isoformat()

    namespace, table = identifier.split(".")
    arrow = to_bronze_arrow(df)

    catalog.create_namespace_if_not_exists(namespace)
    # it not involed with schema it just create table
    tbl = catalog.create_table_if_not_exists(identifier, schema=arrow.schema)

    # 1 transaction = 1 nessie commit included data and watermark
    with tbl.transaction() as tx:
        # schema evolution
        with tx.update_schema() as update:
            update.union_by_name(arrow.schema) # map by name -> add column or change order safe

        if mode == "incremental":
            tx.append(arrow)
            tx.set_properties({WATERMARK_PROP: new_wm})
        else:
            tx.overwrite(arrow)

    print(f"Load {name}: {len(df)} rows -> iceberg.{identifier} ({mode})")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", help="one source in sources.yml")
    parser.add_argument("--all", action="store_true", help="run all sources")
    args = parser.parse_args()

    sources = load_config()
    if args.all:
        targets = sources
    elif args.source:
        targets = {args.source: sources[args.source]}
    else:
        parser.error("need --source <name> or --all")

    catalog = get_catalog()
    for name, cfg in targets.items():
        ingest_by_connector(name, cfg, catalog)

if __name__ == "__main__":
    main()