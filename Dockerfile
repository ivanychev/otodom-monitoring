FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV PATH="$POETRY_HOME/bin:$PATH"

# Use bash
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ADD poetry.lock pyproject.toml /opt/

WORKDIR /opt

RUN python -c 'import urllib.request, sys; print(urllib.request.urlopen(f"{sys.argv[1]}").read().decode("utf8"))' \
    https://install.python-poetry.org  | python3 - && \
    poetry config virtualenvs.create false && \
    poetry install --no-root --only main && \
    rm -rf ~/.cache/pypoetry/{cache,artifacts} && \
    rm -rf /opt/poetry

ADD otodom /opt/otodom
