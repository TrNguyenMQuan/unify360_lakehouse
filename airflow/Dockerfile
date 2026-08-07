# Airflow only orchestration - dependency pipeline store into another venv
ARG AIRFLOW_VERSION=3.1.0
FROM apache/airflow:${AIRFLOW_VERSION}

# install env owner by airflow avoid conflict dependency
USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends make \
 && rm -rf /var/lib/apt/lists/* \
 && mkdir -p /opt/pipeline \
 && chown airflow: /opt/pipeline

USER airflow
RUN mkdir -p /home/airflow/.soda \
 && printf 'send_anonymous_usage_stats: false\n' > /home/airflow/.soda/config.yml
COPY requirements.txt /tmp/requirements.txt
RUN python -m venv /opt/pipeline/venv \
 && /opt/pipeline/venv/bin/pip install --no-cache-dir --upgrade pip \
 && /opt/pipeline/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt
