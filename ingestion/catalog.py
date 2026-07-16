# Create connector to Iceberg catalog (Nessie REST)
from __future__ import annotations
from pyiceberg.catalog import load_catalog
from pyiceberg.catalog.rest import RestCatalog
from ingestion.config import (
    NESSIE_URI,
    NESSIE_WAREHOUSE,
    MINIO_ENDPOINT,
    S3_OPTS
)

def get_catalog() -> RestCatalog:
    # load_catalog(name, **props)
    return load_catalog(
        "nessie",
        **{
            "type": "rest",
            "uri": NESSIE_URI,
            "warehouse": NESSIE_WAREHOUSE,
            "s3.endpoint": MINIO_ENDPOINT,
            "s3.access-key-id": S3_OPTS["key"],
            "s3.secret-access-key": S3_OPTS["key"],
            "s3.path-style-access": "true",
            "s3.region": "us-east-1"
        }
    )