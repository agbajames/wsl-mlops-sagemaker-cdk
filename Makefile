.PHONY: venv install-all install-infra install-pipeline install-scripts test lint format cdk-bootstrap cdk-deploy cdk-destroy upload-seed upsert-pipeline

venv:
	python -m venv .venv
	@echo "Run: source .venv/bin/activate"

install-infra:
	pip install -U pip
	pip install -r infra/cdk/requirements.txt

install-pipeline:
	pip install -U pip
	pip install -r pipeline/requirements.txt

install-scripts:
	pip install -U pip
	pip install -r scripts/requirements.txt

install-all: install-infra install-pipeline install-scripts
	pip install -r dev-requirements.txt

test:
	pytest -q --disable-warnings --maxfail=1 --cov=pipeline --cov-report=term-missing

lint:
	ruff check .
	mypy pipeline

format:
	ruff format .

cdk-bootstrap:
	cd infra/cdk && cdk bootstrap

cdk-deploy:
	cd infra/cdk && cdk deploy --all --require-approval never

cdk-destroy:
	cd infra/cdk && cdk destroy --all --force

upload-seed:
	python scripts/upload_seed_data.py

upsert-pipeline:
	python pipeline/build_pipeline.py --upsert
