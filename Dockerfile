FROM python:3.10-slim-bullseye

ENV PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.3.1 \
    POETRY_HOME="/opt/poetry"

RUN pip install -U pip \
    && apt-get update \
    && apt install -y curl netcat pdftk-java \
    && curl -sSL https://install.python-poetry.org | python -
ENV PATH="${POETRY_HOME}/bin:${PATH}"

WORKDIR /code
COPY poetry.lock pyproject.toml /code/

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-dev

COPY . /code
