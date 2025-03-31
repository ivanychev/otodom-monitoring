FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.6.11 /uv /uvx /bin/

ENV DEBIAN_FRONTEND=noninteractive
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV PATH="$POETRY_HOME/bin:$PATH"
ENV LOGURU_COLORIZE=NO

# Use bash
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ADD uv.lock pyproject.toml /opt/

WORKDIR /opt

RUN uv sync --compile-bytecode --frozen

ADD otodom /opt/otodom
