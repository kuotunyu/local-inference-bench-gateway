# syntax=docker/dockerfile:1.7
FROM ghcr.io/astral-sh/uv:0.11.18 AS uv

FROM python:3.12.13-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH" \
    GATEWAY_DB_PATH=/app/data/gateway.db

WORKDIR /app

COPY --from=uv /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --extra dashboard --no-install-project

COPY gateway ./gateway
COPY dashboard ./dashboard

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin app \
    && mkdir -p /app/data \
    && chown 10001:10001 /app/data

VOLUME ["/app/data"]
EXPOSE 9000
USER 10001:10001

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9000/health', timeout=2).read()"]

CMD ["uvicorn", "gateway.app:app", "--host", "0.0.0.0", "--port", "9000", "--workers", "1"]
