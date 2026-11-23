# Update YouTube metrics for summarized videos

Use this guide to refresh the public YouTube counts of videos you already
summarized, without regenerating any summary.

## Before you begin

- You have a local OKF bundle that contains video notes,
  such as the `docs/` directory of `yt-conferences`.
- You have network access to YouTube.
  If you used a proxy to summarize, pass `--proxy-username` and
  `--proxy-password` again.
- You don't need an LLM, a transcript, or Notion credentials.

## Refresh the metrics

Run the command with `--update-metrics` and point `--output-dir` at the bundle
root:

```bash
yt_summarizer --update-metrics --output-dir ../yt-conferences/docs
```

The command visits every `<root>/<playlist>/<video-id>.md` note and prints a
result like this:

```text
Updating YouTube metrics of stored videos...
Updated 120 video(s); 3 failed.
```

All playlists (conferences) under the root are processed in one run.
Videos are fetched in parallel (one worker per CPU core), and only metadata is requested:
no transcripts, subtitles, or media manifests are downloaded.

## Check the result

Open any video note.
Its `youtube_stats` frontmatter now holds the current values:

```yaml
youtube_stats:
  view_count: 2152
  like_count: 75
  channel_subscriber_count: 41100
```

Review the changes with `git diff`.
Only the `youtube_stats` block should differ.

## Handle failures

A video counts as failed when YouTube returns no metrics for it,
for example because it is private or was deleted.
The command leaves the note untouched and keeps its last known values.
Rerun the command later,
or run with `--log-level DEBUG` and check `yt_summarizer.log` for the cause.

If a count is missing in a successful response,
the command keeps the previous value for that count.

## Related

- [CLI and configuration reference](../references/index.md#filesystem-contract)
- [Run the application](running-application.md)
