# Engine metadata-driven: depend on config to chose connector with full and watermark load
from __future__ import annotations
import argparse
import yaml
import json
from pathlib import Path
import pandas as pd
import pyarrow as pa    # Iceberg write from arrow table
from ingestion.connectors.base import Connector
from ingestion.connectors.csv import CsvConnector
from ingestion.connectors.rest import RestConnector
from ingestion.connectors.jdbc import JdbcConnector
from ingestion.connectors.mongo import MongoConnector
from ingestion.catalog import get_catalog

CONFIG_PATH = "ingestion/config/sources.yml"
STATE_PATH = Path("ingestion/state.json")
META_COLS = ("_source", "_ingested_ad")     # add column add in layer bronze

CONNECTORS: dict[str, type[Connector]] = {
    "csv": CsvConnector,
    "rest": RestConnector,
    "jdbc": JdbcConnector,
    "mongodb": MongoConnector
}

def load_config() -> dict:
    with open(CONFIG_PATH) as file:
        return yaml.safe_load(file)["sources"]

def load_state() -> dict:
    return json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else {}

def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2, default=str))

# pyiceberg write from pyarrow not directly with pandas
def to_bronze_arrow(df: pd.DataFrame) -> pa.Table:
    return pa.Table.from_pandas(df.astype("string"), preserve_index=False)

def ingest_by_connector(name: str, cfg: dict, state: dict, catalog) -> None:
    conn_type = cfg["type"]
    if conn_type not in CONNECTORS:
        raise ValueError(f"Unknown type '{conn_type}'")

    connector: Connector = CONNECTORS[conn_type](cfg)
    mode = cfg.get("load_mode", "full")

    since = state.get(name) if mode == "incremental" else None
    df = connector.extract(since=since)
    if df.empty:
        print(f"{name}: no have new records")
        return

    if mode == "incremental":
        state[name] = df[cfg["watermark"]].max()

    df["_source"] = name
    df["_ingested_at"] = pd.Timestamp.now(tz="UTC").isoformat()

    # target: "bronze.crm_contacts" -> namespace=bronze, table=crm_contacts
    namespace, table = cfg["target_bronze"].split(".")
    identifier = f"{namespace}.{table}"
    arrow = to_bronze_arrow(df)

    catalog.create_namespace_if_not_exists(namespace)   # idemppotent
    tbl = catalog.create_table_if_not_exists(identifier, schema=arrow.schema)

    if mode == "incremental":
        tbl.append(arrow)       # new snapshot
    else:
        tbl.overwrite(arrow)    # full refresh

    print(f"Load {name}: {len(df)} rows -> iceberg.{identifier} ({mode})")

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", help="one source in sources.yml")
    parser.add_argument("--all", action="store_true", help="run all sources")
    args = parser.parse_args()

    sources, state = load_config(), load_state()
    if args.all:
        targets = sources
    elif args.source:
        targets = {args.source: sources[args.source]}
    else:
        parser.error("need --source <name> or --all")

    catalog = get_catalog()
    for name, cfg in targets.items():
        ingest_by_connector(name, cfg, state, catalog)
    save_state(state)

if __name__ == "__main__":
    main()