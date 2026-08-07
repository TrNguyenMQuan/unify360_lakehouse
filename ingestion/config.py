# Use to read and check env
import os
from dotenv import load_dotenv

load_dotenv()

def _require(name: str) -> str:
    val = os.environ.get(name)
    if not val or not val.strip():
        raise RuntimeError(
            f"Miss environment variable '{name}'"
        )
    return val.strip() #remove space

def _get(name: str, default: str) -> str:
    # address/topology: difference from each env, default = local dev
    return os.environ.get(name, default).strip()

# MinIO
MINIO_ENDPOINT = _require("MINIO_ENDPOINT")
MINIO_BUCKET = _require("MINIO_BUCKET")
S3_OPTS = {
    "key": _require("MINIO_ROOT_USER"),
    "secret": _require("MINIO_ROOT_PASSWORD"),
    "client_kwargs": {"endpoint_url": MINIO_ENDPOINT}
}

# Postgres
POSTGRES = dict(
    host=_get("APP_PG_HOST", "localhost"),
    port=int(_get("APP_PG_PORT", "5434")), # because in compose network is postgres-app:5432
    dbname=_require("APP_PG_DB"),
    user=_require("APP_PG_USER"),
    password=_require("APP_PG_PASSWORD")
)

# Mongo
MONGO = dict(
    host=_get("MONGO_HOST", "localhost"),
    port=int(_get("MONGO_PORT", "27017")),
    username=_require("MONGO_USER"),
    password=_require("MONGO_PASSWORD"),
    authSource="admin"
)

# Trino - use by dbt and soda
TRINO_HOST = _get("TRINO_HOST", "localhost")
TRINO_PORT = int(_get("TRINO_PORT", "8080"))

# Nessie
NESSIE_URI= _require("NESSIE_URI")
NESSIE_WAREHOUSE = _require("NESSIE_WAREHOUSE")