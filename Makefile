PYTHON ?= python3

.PHONY: install lint format test data pipeline run

install:
	$(PYTHON) -m pip install -e ".[dev,scrapers]"

lint:
	ruff check .
	ruff format --check .

format:
	ruff format .
	ruff check --fix .

test:
	$(PYTHON) -m pytest -q

data:
	$(PYTHON) scripts/author_sample_data.py

pipeline:
	$(PYTHON) -m perfume_radar.etl.build_dataset

run:
	$(PYTHON) -m streamlit run app.py
