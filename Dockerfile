#checkov:skip=CKV_DOCKER_2:Ensure that HEALTHCHECK instructions have been added to container images
FROM python:3.12-alpine AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY . /app/

RUN apk add --no-cache gcc musl-dev

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

ENV NOTION_TOKEN_FILE='/etc/notion/secrets.txt'
ENV NOTION_DATABASE_ID=''
ENV LLM_MODEL='ollama/llama3.2'
ENV LLM_API_BASE='http://localhost:11434'

ENTRYPOINT ["/app/yt-summarizer"]