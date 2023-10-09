install:
	poetry install

install-poetry:
	curl -sSL https://install.python-poetry.org | python && \
	poetry install

install-poetry-dev:
	curl -sSL https://install.python-poetry.org | python && \
	poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi --only dev

build:
	docker build -t "doc-mgmt:latest" -f "Dockerfile" .

clean:
	find ./ | grep -E "\(__pycache__|\.pyc|\.pyo$\)" | xargs rm -rf && \
	rm -f .coverage && \
	rm -rf coverage && \
	rm -rf .pytest_cache && \
	rm -rf .mypy_cache

backend-up:
	docker-compose --profile backend up -d

backend-down:
	docker-compose --profile backend down

tests-up:
	docker-compose --profile tests up -d

tests-down:
	docker-compose --profile tests down

up: \
	backend-up

down: \
	backend-down

static-check:
	flake8 .
	mypy .

fix-imports:
	isort .

tests-run:
	export ENV_FILE_NAME='.env.tests' && \
	export AWS_DEFAULT_REGION='us-east-1' && \
	poetry run pytest --cov=app --cov-report=term:skip-covered --cov-report=html:coverage --cov-fail-under=90 ./tests

sleep-5:
	sleep 5

tests: \
	tests-up \
	sleep-5 \
	tests-run \
	tests-down


create-tables:
	python scripts/local_db_migration.py create_tables

delete-tables:
	python scripts/local_db_migration.py delete_tables

services-up: \
	tests-up \
	sleep-5 \
	create-tables

services-down: \
	tests-down

run:
	export AWS_DEFAULT_REGION='us-east-1' && uvicorn app.main:app --host localhost --port 8000
