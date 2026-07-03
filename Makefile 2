.PHONY: install lint format test data pipeline run

install:
	pip install -e ".[dev,scrapers]"

lint:
	ruff check .
	ruff format --check .

format:
	ruff format .
	ruff check --fix .

test:
	pytest -q

data:
	python scripts/author_sample_data.py

pipeline:
	python -m perfume_radar.etl.build_dataset

run:
	streamlit run app.py
