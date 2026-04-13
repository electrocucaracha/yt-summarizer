# YouTube Summarizer

<!-- markdown-link-check-disable-next-line -->

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![GitHub Super-Linter](https://github.com/electrocucaracha/yt-summarizer/workflows/Lint%20Code%20Base/badge.svg)](https://github.com/marketplace/actions/super-linter)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

<!-- markdown-link-check-disable-next-line -->

![visitors](https://visitor-badge.laobi.icu/badge?page_id=electrocucaracha.yt-summarizer)
[![Scc Code Badge](https://sloc.xyz/github/electrocucaracha/yt-summarizer?category=code)](https://github.com/boyter/scc/)
[![Scc COCOMO Badge](https://sloc.xyz/github/electrocucaracha/yt-summarizer?category=cocomo)](https://github.com/boyter/scc/)

A Python automation tool that retrieves YouTube videos from a Notion database, extracts their transcripts, generates intelligent summaries using Large Language Models, and updates the database with results.

![Diagram](docs/assets/concept.png)

## Key Features

- **Notion Integration**: Retrieves video records from Notion databases containing YouTube URLs
- **YouTube Transcript Extraction**: Automatically fetches video titles and transcripts
- **LLM-Powered Summaries**: Generates concise summaries and extracts key points using configurable language models
- **Flexible Configuration**: Supports local models via Ollama and cloud-based services through LiteLLM
- **Database Synchronization**: Persists analysis results back to Notion for team collaboration
- **Detailed Logging**: Monitors and troubleshoots the processing pipeline
- **Error Handling**: Gracefully handles unavailable or restricted videos with detailed error messages

## Key Updates

- **Enhanced CLI Error Handling**: The CLI now exits with a specific connection error message when the configured LLM endpoint cannot be reached.
  This includes details about the failing `--api-base` and model values.
- **Improved Logging**: Detailed logs for troubleshooting and monitoring the processing pipeline.

## Use Cases

- **Content Curation**: Summarize video content for knowledge management
- **Research Archives**: Build searchable archives of video summaries
- **Team Collaboration**: Store video insights in Notion for discussion
- **Efficient Reviews**: Extract key points without watching entire videos
- **Documentation**: Create structured knowledge bases from video analysis

## Limitations

- **Age-Restricted Videos**: Cannot process age-restricted YouTube videos as cookie-based authentication is not currently supported by the youtube-transcript-api library
- **Videos Without Transcripts**: Can only process videos that have captions/subtitles enabled
- **Private/Deleted Videos**: Cannot access private, unlisted (without direct link), or deleted videos

## Summary Samples

Playlist executive summary examples now live in the documentation set.
See [docs/explanation/summary-samples.md](docs/explanation/summary-samples.md)
for the full sample collection.
