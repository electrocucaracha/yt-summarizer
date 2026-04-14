# YouTube Summarizer

<!-- markdown-link-check-disable-next-line -->

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![GitHub Super-Linter](https://github.com/electrocucaracha/yt-summarizer/workflows/Lint%20Code%20Base/badge.svg)](https://github.com/marketplace/actions/super-linter)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

<!-- markdown-link-check-disable-next-line -->

![visitors](https://visitor-badge.laobi.icu/badge?page_id=electrocucaracha.yt-summarizer)
[![Scc Code Badge](https://sloc.xyz/github/electrocucaracha/yt-summarizer?category=code)](https://github.com/boyter/scc/)
[![Scc COCOMO Badge](https://sloc.xyz/github/electrocucaracha/yt-summarizer?category=cocomo)](https://github.com/boyter/scc/)

`yt-summarizer` is a Python CLI
that reads YouTube videos from a Notion database,
retrieves transcripts,
generates per-video summaries and main points with an LLM,
and writes the results back to Notion.
It also supports ingesting a full YouTube playlist into the processing queue
and produces an executive summary
that synthesizes the collection.

![Diagram](docs/assets/concept.png)

## Key Features

- **Notion-backed workflow**:
  Reads video records from a Notion database
  and updates them in place.
- **YouTube playlist support**:
  Accepts a `--playlist-url`
  and adds new playlist videos to the current run.
- **Per-video analysis**:
  Generates a concise summary
  and a list of main points for each video.
- **Executive summaries**:
  Produces a synthesized playlist or collection-level executive summary
  at the end of the run.
- **Flexible LLM backends**:
  Works with local Ollama models
  and other LiteLLM-compatible providers.
- **Operational visibility**:
  Includes structured logging
  and clearer connection errors for unreachable LLM endpoints.

## How It Works

1. Load existing video records from Notion.
2. Optionally expand the queue with videos discovered from `--playlist-url`.
3. Fetch each video's title and transcript from YouTube.
4. Generate a summary and main points for each video with the configured LLM.
5. Upsert the results into Notion.
6. Print an executive summary across the processed collection.

## Notion Database Expectations

The CLI updates Notion properties
with these names:

- `Title`
- `URL`
- `Summary`
- `Main Points`

## Use Cases

- Build a shared Notion knowledge base from conference talks and technical playlists.
- Batch-summarize videos already curated in Notion.
- Import a new playlist and immediately generate a higher-level executive brief.
- Capture key points for later review without rewatching full videos.

## Limitations

- Age-restricted videos are not supported by the current transcript retrieval flow.
- Videos without captions or transcripts cannot be summarized.
- Private, deleted, or otherwise inaccessible videos cannot be processed.
- Playlist processing still depends on each individual video being reachable and transcribed.

## Additional Documentation

- [Running the application](docs/how-to/running-application.md)
- [Workflow explanation](docs/explanation/workflow.md)
- [Executive summary samples](docs/explanation/summary-samples.md)
