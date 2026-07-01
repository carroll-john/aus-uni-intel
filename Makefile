PYTHON := .venv/bin/python
PIP := .venv/bin/pip
API_HOST := 127.0.0.1
API_PORT := 8000
WEB_PORT := 3000

.PHONY: bootstrap web-install demo ingest-finance ingest-all test lint format format-check typecheck-py api web dev verify archive-db deploy-check clean-db

.venv/.installed: pyproject.toml
	python3 -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	touch .venv/.installed

bootstrap: .venv/.installed

web-install:
	cd apps/web && npm install

demo: bootstrap ingest-all test

ingest-finance: bootstrap
	$(PYTHON) -m uni_intel.ingestion.ingest_finance --year 2024

ingest-all: bootstrap
	$(PYTHON) -m uni_intel.ingestion.ingest_all

test: bootstrap
	$(PYTHON) -m pytest

lint: bootstrap
	$(PYTHON) -m ruff check src tests

format: bootstrap
	$(PYTHON) -m ruff format src tests

format-check: bootstrap
	$(PYTHON) -m ruff format --check src tests

typecheck-py: bootstrap
	$(PYTHON) -m pyright

api: bootstrap
	$(PYTHON) -m uvicorn uni_intel.api.main:app --reload --host $(API_HOST) --port $(API_PORT)

web: web-install
	cd apps/web && NEXT_PUBLIC_API_BASE_URL=http://$(API_HOST):$(API_PORT) npm run dev

dev: bootstrap web-install ingest-all
	@trap 'kill 0' INT TERM EXIT; \
	$(PYTHON) -m uvicorn uni_intel.api.main:app --host $(API_HOST) --port $(API_PORT) & \
	cd apps/web && NEXT_PUBLIC_API_BASE_URL=http://$(API_HOST):$(API_PORT) npm run dev

verify: bootstrap web-install ingest-all test lint format-check
	cd apps/web && npm run lint && npm run typecheck && npm run build
	@trap 'kill $$API_PID' EXIT; \
	$(PYTHON) -m uvicorn uni_intel.api.main:app --host $(API_HOST) --port $(API_PORT) >/tmp/uni-intel-api.log 2>&1 & \
	API_PID=$$!; \
	sleep 2; \
	cd apps/web && NEXT_PUBLIC_API_BASE_URL=http://$(API_HOST):$(API_PORT) npm run smoke

archive-db:
	test -f data/warehouse/university_intel.duckdb
	gzip -c data/warehouse/university_intel.duckdb > data/warehouse/university_intel.duckdb.gz

deploy-check: verify archive-db
	git diff --check
	@echo "Deployable state prepared. Commit data/warehouse/university_intel.duckdb.gz when data changed."

clean-db:
	rm -f data/warehouse/university_intel.duckdb data/warehouse/prototype_check.duckdb
