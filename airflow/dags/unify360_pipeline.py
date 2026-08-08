# with these airflow need create dag by taskflow api
from __future__ import annotations
from datetime import timedelta
import pendulum
from airflow.sdk import dag, task

PROJECT_DIR = "/opt/project"    # repo mount in container
VENV = "/opt/pipeline/venv/bin"
SODA_CONF = "data_quality/configuration.docker.yml"     # soda can replace ${VAR}
TIME_ENV = {"UNIFY_REFERENCE_NOW" : "{{ data_interval_end | ds }}"} # naive

@dag(
    dag_id="unify360_pipeline",
    schedule="@daily",
    start_date=pendulum.datetime(2026, 8, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,  # make sure only 1 pipeline run
    default_args={"retries": 0},
    tags=["unify360", "lakehouse"],
    doc_md=__doc__
)

def unify360_pipeline():
    # in real production this task dont exists, the data will create by source system
    @task.bash(cwd=PROJECT_DIR, env=TIME_ENV, append_env=True, retries=1)
    def seed() -> str:
        return f"{VENV}/python -m generators.seed_all"

    @task.bash(
        cwd=PROJECT_DIR,
        env=TIME_ENV,
        append_env=True,
        retries=2,
        retry_delay=timedelta(minutes=1)
    )
    def ingest() -> str:
        return f"{VENV}/python -m ingestion.engine --all"

    @task.bash(cwd=PROJECT_DIR)
    def build() -> str:
        return f"{VENV}/dbt build --project-dir dbt --profiles-dir dbt"

    @task.bash( # call script gate without make
        cwd=PROJECT_DIR,
        # scan and seed must run on the same time
        env={**TIME_ENV, "SODA": f"{VENV}/soda", "SODA_CONF": SODA_CONF},
        append_env=True
    )
    def scan(layer: str) -> str: # dynamic task generation
        return f"scripts/soda_gate.sh {layer}"

    # 3 layer seperate
    scans = [scan.override(task_id=f"scan_{layer}")(layer) for layer in ("bronze", "silver", "gold")]

    seed() >> ingest() >> build() >> scans

unify360_pipeline()