# Running the Application

The application requires a Notion API token.
By default, it reads the token from `/etc/notion/secrets.txt`.
You can either:

1. **Create the token file** (recommended for production):

```bash
echo "your-notion-token-here" > /etc/notion/secrets.txt
chmod 600 /etc/notion/secrets.txt
```

2. **Or use environment variable** (for quick testing):

```bash
export NOTION_TOKEN="your-notion-token-here"
```

Then execute the CLI with your Notion database ID:

```bash
yt_summarizer --notion-db-id "your-database-id" --model "ollama/llama3.2" --api-base "http://localhost:11434"
```

Or specify a custom token file location:

```bash
yt_summarizer --notion-db-id "your-database-id" --notion-token-file "/path/to/token/file"
```

## Configuration Options

- `--notion-db-id`: Notion database ID (required, or set `NOTION_DATABASE_ID` environment variable)
- `--notion-token-file`: Path to file containing Notion API token (default: `/etc/notion/secrets.txt`, or set `NOTION_TOKEN_FILE`)
- `--model`: LLM model identifier (default: `ollama/llama3.2`, or set `LLM_MODEL`)
- `--api-base`: LLM API base URL (default: `http://localhost:11434`, or set `LLM_API_BASE`)
- `--log-level`: Logging verbosity - DEBUG, INFO, WARNING, ERROR, or CRITICAL (default: INFO)

If you use Ollama locally, make sure the service is running before starting the CLI.
When the configured LLM endpoint cannot be reached, the CLI now exits with a specific connection error that includes the failing `--api-base` and model values.

## Environment Variables

| Name               | Default                  | Description                                        |
| ------------------ | ------------------------ | -------------------------------------------------- |
| NOTION_TOKEN       |                          | Notion API token - overrides token file (optional) |
| NOTION_TOKEN_FILE  | /etc/notion/secrets.txt  | Path to file containing Notion API token           |
| NOTION_DATABASE_ID |                          | Notion database ID containing videos (required)    |
| LLM_MODEL          | ollama/llama3.2          | LLM model identifier for analysis                  |
| LLM_API_BASE       | <http://localhost:11434> | Base URL for the LLM API endpoint                  |

## Running in Docker

When running with Docker, mount the secrets file:

```bash
docker run -v /path/to/secrets.txt:/etc/notion/secrets.txt \
  -e NOTION_DATABASE_ID="your-database-id" \
  yt-summarizer:latest
```

Or pass the token via environment variable:

```bash
docker run \
  -e NOTION_TOKEN="your-notion-token-here" \
  -e NOTION_DATABASE_ID="your-database-id" \
  yt-summarizer:latest
```

## Running Tests

To run the test suite, use the `make test` command.
This will clean up any build artifacts, ensure the required dependencies are installed, and execute the tests using `tox`.

```bash
make test
```

Ensure that you have the necessary tools installed, such as `uvx`, which will be automatically installed if missing.

## Troubleshooting

### Common Issues

- **Unreachable LLM Endpoint**:
  Ensure the `--api-base` URL is correct and the LLM service is running.
  The CLI will provide a specific connection error message with details about the failing `--api-base` and model values.
