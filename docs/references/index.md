# CLI and configuration reference

## Command

```text
yt_summarizer [OPTIONS]
```

The command processes the union of videos found in the configured Notion
database, playlist, and filesystem bundle. Duplicate URLs are processed once.
It always attempts to generate an executive summary from the processed video
summaries.

## Options

| Option                | Default                                  | Environment variable | Purpose                                            |
| --------------------- | ---------------------------------------- | -------------------- | -------------------------------------------------- |
| `--notion-db-id`      | none                                     | `NOTION_DATABASE_ID` | Notion database to read and update                 |
| `--notion-token-file` | `/etc/notion/secrets.txt`                | `NOTION_TOKEN_FILE`  | File containing the Notion token                   |
| `--output-dir`        | `docs` without Notion; unset with Notion | `OUTPUT_DIR`         | OKF bundle root                                    |
| `--model`             | `ollama/llama3.2`                        | `LLM_MODEL`          | LiteLLM model identifier                           |
| `--api-base`          | Ollama local endpoint for most models    | `LLM_API_BASE`       | LLM API base URL                                   |
| `--playlist-url`      | none                                     | none                 | YouTube playlist to add to the queue               |
| `--proxy-username`    | none                                     | `PROXY_USERNAME`     | Webshare proxy username                            |
| `--proxy-password`    | none                                     | `PROXY_PASSWORD`     | Webshare proxy password                            |
| `--log-level`         | `INFO`                                   | none                 | `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL` |

`NOTION_TOKEN` is not a Click option. When set, it overrides the token file.
The CLI does not require Notion configuration when filesystem mode is active.

## Notion contract

Input records are normalized from properties named `URL`, `Title`, `Transcript`,
`Summary`, and either `Main points` or `Main Points`.
The `URL` property is required for a record to enter the queue.

Writes use these property names:

```text
Title
URL
Summary
Main Points
```

Existing pages are updated using their internal page ID.
Playlist videos that are not already present are created as new pages.

## Filesystem contract

The filesystem backend writes Markdown documents with OKF YAML frontmatter.
Titles are converted to lowercase slugs for directories and playlist files.
Video files use the YouTube video ID as their filename.

```text
<root>/
├── index.md
├── <playlist-slug>.md
└── <playlist-slug>/
  ├── index.md
  ├── README.md
  └── <video-id>.md
```

Video documents contain `Summary`, `Main Points`, and `Citations` sections.
Playlist documents contain an `Executive Summary` and links to the video
documents.

## LLM limits

| Result                |   Maximum length |
| --------------------- | ---------------: |
| Per-video summary     | 2,000 characters |
| Per-video main points | 2,000 characters |
| Executive summary     | 6,000 characters |

These limits are instructions to the model; the final executive summary is
also truncated to 6,000 characters if a provider returns more.

## Python modules

The package is organized around these responsibilities:

- `yt_summarizer`: Click entry point, option resolution, progress output, and
  error handling.
- `service`: Coordinates storage, YouTube retrieval, LLM analysis, retries, and
  executive-summary reduction.
- `notion`: Converts Notion API properties and performs database reads and page
  writes.
- `okf`: Reads and writes the local Markdown knowledge bundle.
- `youtube`: Retrieves titles and transcripts and supports the configured proxy.
- `llm`: Wraps LiteLLM and implements summary, main-point, and executive-summary
  prompts.
- `model`: Defines the `YouTubeVideo` data model and persisted-content hashing.
