FROM python:3.12-alpine AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY . /app/

RUN apk add --no-cache gcc=15.2.0-r2 musl-dev=1.2.5-r21

RUN uv sync --no-editable && \
    uvx pex -o /tmp/yt-summarizer -c yt_summarizer --include-tools .

FROM python:3.12-alpine

COPY --from=builder /tmp/yt-summarizer /app/yt-summarizer

RUN addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser && \
    chown -R appuser:appuser /app && \
    mkdir -p /etc/notion && \
    chown appuser:appuser /etc/notion

WORKDIR /app

USER appuser

ENV NOTION_DATABASE_ID=''
ENV LLM_MODEL='ollama/llama3.2'
ENV LLM_API_BASE='http://localhost:11434'

HEALTHCHECK NONE

ENTRYPOINT ["/app/yt-summarizer"]
