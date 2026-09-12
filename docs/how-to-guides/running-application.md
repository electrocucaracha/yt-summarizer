# Run the application

`yt-summarizer` supports two storage modes:

- **Filesystem mode** requires no Notion credentials and writes an OKF bundle to
  `docs/` by default.
- **Notion mode** reads and updates a Notion database. You can also enable
  filesystem output to keep a local copy.

## Run without Notion

Provide a playlist URL to populate a local bundle:

```bash
yt_summarizer \
  --playlist-url "https://www.youtube.com/playlist?list=PLAYLIST_ID" \
  --model "ollama/llama3.2" \
  --api-base "http://localhost:11434"
```

Use `--output-dir` to write somewhere other than `docs/`:

```bash
yt_summarizer \
  --playlist-url "https://www.youtube.com/playlist?list=PLAYLIST_ID" \
  --output-dir "knowledge" \
  --model "ollama/llama3.2"
```

## Run with Notion

The application reads a Notion token from `/etc/notion/secrets.txt` by default.
You can either:

1. **Create the token file** (recommended for production):

```bash
echo "your-notion-token-here" > /etc/notion/secrets.txt
chmod 600 /etc/notion/secrets.txt
```

1. **Or use environment variable** (for quick testing):

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

You can combine Notion input with a playlist. Existing URLs are skipped, and
new playlist videos are added to the current processing queue:

```bash
yt_summarizer \
  --notion-db-id "your-database-id" \
  --playlist-url "https://www.youtube.com/playlist?list=PLAYLIST_ID" \
  --model "ollama/llama3.2"
```

## Configuration options

- `--notion-db-id`: Notion database ID (required, or set `NOTION_DATABASE_ID` environment variable)
- `--notion-token-file`: Path to file containing Notion API token (default: `/etc/notion/secrets.txt`, or set `NOTION_TOKEN_FILE`)
- `--model`: LLM model identifier (default: `ollama/llama3.2`, or set `LLM_MODEL`)
- `--api-base`: LLM API base URL (default: `http://localhost:11434`, or set `LLM_API_BASE`)
- `--playlist-url`: Optional YouTube playlist URL to add to the queue
- `--output-dir`: OKF bundle root. Defaults to `docs` in filesystem mode, or is
  disabled when omitted with Notion mode.
- `--proxy-username`: Optional Webshare proxy username, or set `PROXY_USERNAME`
- `--proxy-password`: Optional Webshare proxy password, or set `PROXY_PASSWORD`
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
| LLM_API_BASE       | `http://localhost:11434` | Base URL for the LLM API endpoint                  |
| OUTPUT_DIR         |                          | OKF bundle root                                    |
| PROXY_USERNAME     |                          | Optional Webshare proxy username                   |
| PROXY_PASSWORD     |                          | Optional Webshare proxy password                   |

`NOTION_TOKEN` takes precedence over `NOTION_TOKEN_FILE` when both are set.
For models whose name starts with `github_copilot/`, the application uses the
provider default endpoint unless `--api-base` is explicitly supplied.

## Notion database schema

The database must expose a URL property named `URL`.
The application reads these properties when present:

- `ID` is used internally to update an existing page.
- `Title` stores the YouTube title.
- `URL` stores the canonical video URL.
- `Transcript` can provide an existing transcript, although the current
  filesystem writer does not persist it.
- `Summary` stores the generated summary.
- `Main points` or `Main Points` stores the generated bullet points.

When writing to Notion, the application updates `Title`, `URL`, `Summary`, and
`Main Points`. Records without a URL are skipped.

## Run in Docker

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

## Run the tests

To run the test suite, use the `make test` command.
This will clean up any build artifacts, ensure the required dependencies are installed, and execute the tests using `tox`.

```bash
make test
```

Ensure that you have the necessary tools installed, such as `uvx`, which will be automatically installed if missing.

## Troubleshoot common problems

### Common Issues

- **Unreachable LLM Endpoint**:
  Ensure the `--api-base` URL is correct and the LLM service is running.
  The CLI will provide a specific connection error message with details about the failing `--api-base` and model values.

- **Video cannot be summarized**:
  The video may be private, deleted, age-restricted, unplayable, missing
  captions, or missing captions in the supported languages: `es`, `es-419`,
  `en`, `en-US`, and `en-GB`.

- **Playlist extraction fails**:
  Verify that the playlist URL is public and that `yt-dlp` can reach YouTube.

- **Notion authentication fails**:
  Check the token value, database ID, and that the integration has access to
  the database. An empty token file is rejected.
