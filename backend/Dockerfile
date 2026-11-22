# syntax=docker/dockerfile:1
FROM python:3.14-slim-trixie AS builder
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --no-install-project

FROM python:3.14-slim-trixie
# Security fixes not yet in the base image (CI passes a daily UPGRADE_EPOCH so the build cache
# does not keep a stale upgrade layer), and no system pip: the app runs from the uv venv, and
# pip's vendored libraries (msgpack, setuptools, urllib3) were the image's open CVEs (CWYD-6).
ARG UPGRADE_EPOCH
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf "$(python -c 'import ensurepip, os; print(os.path.dirname(ensurepip.__file__))')" \
    && python -m pip uninstall -y --root-user-action=ignore pip \
    && useradd --system --uid 10001 --no-create-home app
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY app ./app
COPY alembic.ini ./
COPY migrations ./migrations
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER app
EXPOSE 8000
# Schema first (A1): a failed migration stops the container instead of serving a stale schema.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
