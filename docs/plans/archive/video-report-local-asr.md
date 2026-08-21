# Video report local ASR migration

Status: Complete
Last updated: 2026-07-26

## Goal

Replace the video-report skill's Groq-dependent transcription fallback with a local Apple Silicon workflow led by Qwen3-ASR.

## Current contract

- In scope: use `mlx-qwen3-asr` with `Qwen/Qwen3-ASR-1.7B` as the default no-caption backend; normalize Chinese with local OpenCC `s2twp.json`; support language and bounded domain-context hints; keep audio and transcripts task-local; preserve a clean failure when the local CLI, OpenCC, or model is unavailable.
- Out of scope: changing the HTML/report contract, bundling model weights, requiring SoundScribe/MacWhisper, enabling cloud ASR, or adding diarization dependencies.
- Acceptance criteria: the fallback works without API keys; the wrapper passes deterministic audio/model/language/context arguments and writes a non-empty clean transcript; Groq helper/code/docs/tests are removed; existing caption and report tests remain green; live install and release gates pass.

## Decisions

- **Confirmed** — Remove Groq as a skill dependency and do not read `GROQ_API_KEY` or call a remote transcription API.
- **Confirmed** — Use the Apple Silicon `mlx-qwen3-asr` CLI and default to the accuracy-oriented `Qwen/Qwen3-ASR-1.7B`.
- **Confirmed** — Normalize the clean transcript with OpenCC `s2twp.json` by default; allow `s2t.json` or explicit opt-out for special source material.
- **Confirmed** — Default inference is `offline-cache-only`; model download requires the explicit one-time `--allow-model-download` flag and is recorded separately in the sidecar.
- **Confirmed** — Keep MacWhisper/WhisperKit as an optional human-selected second engine for recordings with long Chinese/English segment switches, not a required automation dependency.
- **Assumed** — Automatic language detection is the default; callers should force `Chinese` or `English` when the source language is known and provide `--context` for domain vocabulary.

## Progress and evidence

- `mlx-qwen3-asr` 0.3.5 is installed in the isolated `uv` tool environment; doctor passes for MLX and ffmpeg. OpenCC 1.4.1 is installed through Homebrew.
- Current upstream documentation confirms Apple Silicon CLI support, local core ASR without a token, 1.7B model selection, language forcing, stdout output, and domain vocabulary context.
- A real six-second Taiwan Mandarin smoke sample passed through the 1.7B model and OpenCC, producing a non-empty Traditional Chinese transcript. An earlier invalid 0.57-second synthetic sample also exposed that context hints must stay narrow.
- Forward-test confirmed the local model snapshot is complete and identified two contract gaps now addressed: captions-unavailable exit 1 is an expected fallback signal, and normal inference must prevent implicit model-network lookup.
- Verification complete: `27 passed, 14 subtests passed`; live install visible; real 1.7B inference passed in normal and `offline-cache-only` modes; forward-test and adversarial review passed; `tools/verify-release.sh` finished with `portable release gates passed`.
