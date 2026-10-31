FROM python:3.12-alpine3.24 AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY . /app/

# hadolint ignore=DL3018
RUN apk add --no-cache build-base

RUN uv sync --no-editable && \
    uvx pex -o /tmp/yt-summarizer -c yt_summarizer --include-tools .

FROM python:3.12-alpine3.24

COPY --from=builder /tmp/yt-summarizer /app/yt-summarizer

RUN addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser && \
    mkdir -p /etc/notion && \
    chown -R appuser:appuser /app /etc/notion

WORKDIR /app

USER 1000:1000

ENV NOTION_DATABASE_ID=''
ENV LLM_MODEL='ollama/llama3.2'
ENV LLM_API_BASE='http://localhost:11434'

HEALTHCHECK NONE

ENTRYPOINT ["/app/yt-summarizer"]
