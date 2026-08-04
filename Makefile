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

# Negative test: test create error in another branch because with version nessie used dont can use nessie cli
NESSIE    := http://localhost:19120/api/v2
DQ_BRANCH := dq_sandbox
TRINO_DQ  := docker exec lakehouse-trino trino --catalog iceberg_dq --schema bronze --execute

.PHONY: dq-branches dq-branch dq-clean dq-scan dq-inject-null dq-inject-dup dq-inject-drop

dq-branches:	## list nessie branch
	@curl -s $(NESSIE)/trees | python3 -c "import sys,json;[print(' ',r['type'],r['name'],r['hash'][:12]) for r in json.load(sys.stdin)['references']]"

dq-branch:	## create nessise branch dq_sandbox from main
	@H=$$(curl -s $(NESSIE)/trees | python3 -c "import sys,json;print([r for r in json.load(sys.stdin)['references'] if r['name']=='main'][0]['hash'])") ; \
	 curl -s -X POST "$(NESSIE)/trees?name=$(DQ_BRANCH)&type=BRANCH" \
	   -H 'Content-Type: application/json' \
	   -d "{\"type\":\"BRANCH\",\"name\":\"main\",\"hash\":\"$$H\"}" | python3 -m json.tool

dq-clean:	## delete branch dq_sandbox -> rollback
	@H=$$(curl -s $(NESSIE)/trees | python3 -c "import sys,json;print([r for r in json.load(sys.stdin)['references'] if r['name']=='$(DQ_BRANCH)'][0]['hash'])") ; \
	 curl -s -X DELETE "$(NESSIE)/trees/$(DQ_BRANCH)@$$H" > /dev/null && echo ">> delete branch $(DQ_BRANCH)"

dq-scan:	## soda scan bronze in dq_sandbox in negative fail = success
	@$(SODA) scan -d bronze_dq -c $(SODA_CONF) data_quality/checks/bronze_checks.yml ; \
	 code=$$? ; \
	 if [ $$code -ge 2 ]; then echo ">> Soda FAIL (exit $$code) - expected output of negative test" ; fi ; \
	 exit 0

dq-inject-null:	## Error 1 (completeness): 3 row contact_email = NULL
	@$(TRINO_DQ) "INSERT INTO crm_contacts SELECT CAST(NULL AS varchar), first_name, last_name, company, lead_source, campaign, created_date, industry, _source, _ingested_at FROM crm_contacts LIMIT 3"
	@echo ">> Expected: missing_count(contact_email) = 0 -> FAIL, value 3"

dq-inject-dup:	## Error 2 (consistency): duplicate 5 rows
	@$(TRINO_DQ) "INSERT INTO crm_contacts SELECT * FROM crm_contacts WHERE contact_email IS NOT NULL LIMIT 5"
	@echo ">> Expected: duplicate_count(contact_email) = 0 -> FAIL, value 5"

dq-inject-drop:	## Error 3 (schema): DROP COLUMN company
	@$(TRINO_DQ) "ALTER TABLE crm_contacts DROP COLUMN company"
	@echo ">> Expected: Schema Check -> FAIL (thieu company) + column_count = 10 -> FAIL (con 9)"
