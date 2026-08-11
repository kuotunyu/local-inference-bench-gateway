FROM python:3.12.13-slim-bookworm

WORKDIR /smoke
COPY docker/smoke/mock_backend.py docker/smoke/smoke_client.py ./

RUN groupadd --gid 10002 smoke \
    && useradd --uid 10002 --gid 10002 --no-create-home --shell /usr/sbin/nologin smoke

USER 10002:10002
