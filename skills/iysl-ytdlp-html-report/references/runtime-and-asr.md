# Runtime and ASR

## Source preparation

`scripts/prepare_source.mjs` accepts one public video URL and delegates metadata
and captions to `extract_transcript.mjs`. It preserves the resolved media ID in
the manifest, so an X or redirect URL does not determine artifact names.

When captions are unavailable, the only bundled fallback is local
`mlx-qwen3-asr` with `Qwen/Qwen3-ASR-1.7B`. Audio download uses yt-dlp with
`--no-playlist`, bounded audio format selection, concurrent fragments, and no
progress output. The fallback writes audio and transcript artifacts inside the
task run directory.

The Qwen wrapper is offline-cache-first. Use `--allow-model-download` only for
the explicit first-time model bootstrap; do not copy model cache paths into a
reader-facing report. OpenCC converts Chinese output to `s2twp.json` by default.

No script in this package reads browser cookies, browser storage, credentials,
or account sessions. A missing local ASR backend is a stop condition; metadata
alone is not transcript evidence and must not produce a report.

## Finalization

`scripts/finalize_report.mjs` is offline once the spec and manifest exist. It
validates the v2 spec, renders Markdown and HTML from the same spec, builds the
operator sidecar, and runs `validate_report_artifacts.mjs` for fresh section,
anchor, path, reader-leak, and sidecar checks.
