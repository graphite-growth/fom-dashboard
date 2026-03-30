FROM python:3.12-slim-bookworm AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install production dependencies only (exclude dev group: pytest, ruff, mypy, etc.)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv lock && uv sync --no-install-project --no-editable --no-dev

# Copy the project into the image
ADD . /app

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv lock && uv sync --no-editable --no-dev

FROM python:3.12-slim

WORKDIR /app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY *.py /app/
COPY app/ /app/app/
ENV PATH="/app/.venv/bin:$PATH"
