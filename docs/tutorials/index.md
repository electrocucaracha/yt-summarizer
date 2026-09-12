# Tutorial: summarize a playlist locally

In this tutorial, you will run `yt-summarizer` without a Notion account.
The application will discover the videos in a YouTube playlist, generate a
summary and main points for each video, and write an OKF knowledge bundle under
`docs/`.

This path uses Ollama locally, so your transcript content stays on your machine
apart from requests made to YouTube.

## Before you begin

You need:

- Python 3.10, 3.11, or 3.12.
- An Ollama installation with a model available locally.
- A YouTube playlist whose videos have captions in English or Spanish.

Install the project from its repository:

```bash
git clone https://github.com/electrocucaracha/yt-summarizer.git
cd yt-summarizer
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
```

Start Ollama and download the default model:

```bash
ollama serve
ollama pull llama3.2
```

Run the summarizer with a playlist URL:

```bash
yt_summarizer \
  --playlist-url "https://www.youtube.com/playlist?list=PLAYLIST_ID" \
  --model "ollama/llama3.2" \
  --api-base "http://localhost:11434"
```

The command creates or updates these files:

```text
docs/
├── index.md
├── <playlist-slug>.md
└── <playlist-slug>/
    ├── index.md
    ├── README.md
    └── <youtube-video-id>.md
```

Open `<playlist-slug>.md` for the executive summary, or open the individual
video documents for the generated summary and main points.

## What you learned

You ran the complete local workflow without configuring Notion.
The same command can be pointed at another output directory with
`--output-dir`; see the [configuration reference](../references/index.md) for
the full option list.
