# Troubleshooting

Classify failures by layer before changing the path:

- URL or metadata: unsupported host, playlist, private video, redirect, DNS,
  or yt-dlp metadata failure.
- Captions: extractor returns `captions-unavailable`; retain the manifest and
  resolved ID before trying audio.
- Audio: yt-dlp format, HLS, network, disk, or partial-file failure.
- ASR: missing `mlx-qwen3-asr`, missing model cache, MLX runtime failure, or
  OpenCC failure. Stop with the exact layer and do not use metadata as content.
- Spec: invalid evidence refs, missing block type, unsupported chart, unsafe
  URL, or reader-facing local path; repair the JSON, not the validator.
- Presentation: render or artifact validator failure; keep operator detail in
  the sidecar and do not ship a second unverified HTML.

Do not solve a browser or permission blocker by enabling cookies, scraping a
paywall, calling an unconfigured cloud ASR service, or silently weakening a
deterministic assertion.
