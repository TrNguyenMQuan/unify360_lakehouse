# Makefile - one entrypoint for any operation in this project

SHELL := /bin/bash

# Config
VENV		:= .venv/bin
PY			:= $(VENV)/python
SODA 		:= $(VENV)/soda
TRINO 		:= docker exec lakehouse-trino trino
SODA_CONF	:= data_quality/configuration.yml

# Incremental table: reset watermark = drop table
INCREMENTAL_TABLES	:= app_users app_subscriptions app_events

.DEFAULT_GOAL	:= help
.PHONY: help up down ps seed ingest ingest-reset build test scan verify lint

help:  ## list entire all cmd already had
	@grep -E '^[a-zA-Z_%-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

up:	## for container
	docker compose up -d

down:	## down container without volume
	docker compose down

ps:		## check status
	docker compose ps

seed:	## generate seed data from 4 sources
	$(if $(NOW),UNIFY_REFERENCE_NOW=$(NOW)) $(PY) -m generators.seed_all

ingest:	## ingest 4 source into bronze
	$(PY) -m ingestion.engine --all

ingest-reset: ## ingest again must to drop incremental tall
	@for t in $(INCREMENTAL_TABLES); do \
		echo ">> drop iceberg.bronze.$$t" ; \
		$(TRINO) --execute "DROP TABLE IF EXISTS iceberg.bronze.$$t" ; \
		done
		$(MAKE) ingest

build:	## dbt build
	cd dbt && ../$(VENV)/dbt build --profiles-dir .

test:	## dbt test
	cd dbt && ../$(VENV)/dbt test --profiles-dir .

scan-%:	## scan 1 layer
	@$(SODA) scan -d $* -c $(SODA_CONF) data_quality/checks/$*_checks.yml ; \
		code=$$? ; \
		if [ $$code -le 1 ]; then \
		[ $$code -eq 1 ] && echo ">> [$*] WARNING" ; \
		exit 0 ; \
		else exit $$code ; fi

scan:	## scan entire
	@$(MAKE) scan-bronze scan-silver scan-gold

verify:	## gate full = dbt test + scan entire
	@$(MAKE) test scan

lint:	## ruff check entire repo
	$(VENV)/ruff check .

refresh: ## run entire pipeline again
	@$(MAKE) seed
	@$(MAKE) ingest-reset
	@$(MAKE) build