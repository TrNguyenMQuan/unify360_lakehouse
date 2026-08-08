#!/usr/bin/env bash
# DAG will call this file to easy read the log because make can dont print log it just throw exit code
# Makefile use this logic date because with soda can crash before run check
set -uo pipefail

# thiếu tham số thì nổ ngay kèm thông báo (fail loudly, không chạy mù)
LAYER="${1:?usage: soda_gate.sh <bronze|silver|gold>}"

# Env override được -> cùng script chạy được ở host (.venv) lẫn container (/opt/pipeline/venv)
SODA="${SODA:-.venv/bin/soda}"
SODA_CONF="${SODA_CONF:-data_quality/configuration.yml}"
CHECKS="${CHECKS_DIR:-data_quality/checks}/${LAYER}_checks.yml"
REFERENCE_NOW="${UNIFY_REFERENCE_NOW:-$(date -u +%F)}" # time point logic not real time use for backfill

out="$("$SODA" scan -d "$LAYER" -c "$SODA_CONF" -v "UNIFY_REFERENCE_NOW=$REFERENCE_NOW" "$CHECKS" 2>&1)"
code=$?

echo "$out"   # log in Airflow

# BẰNG CHỨNG TRƯỚC, EXIT CODE SAU.
if ! grep -q "Scan summary" <<<"$out"; then
  echo ">> [$LAYER] SODA CRASHED before scanning (soda exit $code)"
  exit 3
fi

if [ "$code" -eq 1 ]; then
  echo ">> [$LAYER] WARNING only - not blocking"
  exit 0
fi

exit "$code"
