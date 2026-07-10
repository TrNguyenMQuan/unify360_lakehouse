# Engine metadata-driven: depend on config to chose connector with full and watermark load
from __future__ import annotations
import argparse
import yaml
import pandas as pd
from pathlib import Path
import json
from ingestion.connectors.base import Connector
from ingestion.connectors.csv import CsvConnector
from ingestion.connectors.rest import RestConnector
from ingestion.connectors.jdbc import JdbcConnector
from ingestion.connectors.mongo import MongoConnector
from ingestion.config import S3_OPTS, MINIO_BUCKET as BUCKET

CONFIG_PATH = "ingestion/config/sources.yml"
STATE_PATH = Path("ingestion/state.json")

# type in config -> class connector, add source = add 1 row
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

def ingest_by_connector(name: str, cfg: dict, state: dict) -> None:
    conn_type = cfg["type"]
    if conn_type not in CONNECTORS:
        raise ValueError(f"Unknown type '{conn_type}")

    # select connector
    connector: Connector = CONNECTORS[conn_type](cfg)
    mode = cfg.get("load_mode", "full")

    # extract to df
    since = state.get(name) if mode == "incremental" else None
    df = connector.extract(since=since)

    if df.empty:
        print(f"{name} doent have new record")
        return

    # add metadata bronze
    df["_source"] = name
    df["_ingested_at"] = pd.Timestamp.now(tz="UTC")

    # write parquet into minio
    layer, table = cfg["target_bronze"].split(".")
    base = f"s3://{BUCKET}/{layer}/{table}"

    if mode == "incremental":
        ts = pd.Timestamp.now(tz="UTC").strftime("%Y%m%dT%H%M%S")
        path = f"{base}/part-{ts}.parquet"          # append new file
        state[name] = df[cfg["watermark"]].max()    # update high-watermark
    else:
        path = f"{base}/data.parquet"

    df.to_parquet(path, storage_options=S3_OPTS, index=False)
    print(f"Load {name} : {len(df)} rows into {path}")

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

    for name, cfg in targets.items():
        ingest_by_connector(name, cfg, state)
    save_state(state)

if __name__ == "__main__":
    main()