FROM python:3.10

ENV DEBIAN_FRONTEND=noninteractive
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV PATH="$POETRY_HOME/bin:$PATH"

# Use bash
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN curl -sSL https://install.python-poetry.org  | POETRY_VERSION=1.2.0 python3 -

ADD otodom /opt/otodom
ADD poetry.lock pyproject.toml /opt/

WORKDIR /opt

RUN poetry config virtualenvs.create false && \
    poetry install --no-root --no-dev && \
    rm -rf ~/.cache/pypoetry/{cache,artifacts} && \
    rm -rf /opt/poetry