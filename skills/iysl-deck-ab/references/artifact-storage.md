# Artifact Storage

## Contract

Use this contract when `$iysl-deck-ab` work needs file-backed artifacts. Keep artifacts in one run folder so chat decisions, outline truth, prompts, anchors, images, and review notes do not drift apart.

## When To Create A Run Folder

Create a run folder when any condition applies:

- more than 3 slides
- subagent work
- Mode A and Mode B are both produced
- API production prompt pack
- style anchor/reference image workflow
- image generation outputs
- second or later correction round
- user asks to save artifacts

Small one-off answers may stay in chat unless the user asks for files.

## Location And Name

Prefer the user-specified deck/project workspace. If none is specified, use the current Codex workspace:

```text
work/iysl-deck-ab-runs/YYYYMMDD-HHMMSS-<short-topic-slug>/
```

Before writing, report the planned path. If writing into Google Drive, a repo, or another user folder, create a new folder and do not overwrite existing files. Do not scatter intermediates across Desktop, Downloads, the skill package, `/tmp`, or multiple project folders.

## Folder Structure

```text
manifest.md
00_source/
  source_index.md
  producer_notes.md
01_outline/
  deck_outline.md
02_prompts/
  mode_a_prompts.md
  mode_b_prompts.md
  visible_label_whitelists.md
03_anchors/
  anchor_manifest.md
04_generation/
  api_request_notes.md
  images/
05_review/
  qa_report.md
  prompt_patches.md
```

## File Responsibilities

- `manifest.md`: run id, created time, topic, target language, source paths/links, current source of truth, output modes, anchor paths, status.
- `00_source/source_index.md`: source list and citation method. Do not copy source documents unless the user asks or pasted the text in the current conversation.
- `00_source/producer_notes.md`: deck-usable notes only; each external claim must map to source index.
- `01_outline/deck_outline.md`: Phase 1 source of truth with one `STYLE_INSTRUCTIONS` block and full slide outline.
- `02_prompts/mode_a_prompts.md`: one independent Mode A prompt per slide.
- `02_prompts/mode_b_prompts.md`: one independent Mode B prompt per slide.
- `02_prompts/visible_label_whitelists.md`: Mode B whitelist and rationale.
- `03_anchors/anchor_manifest.md`: reference image/style anchor paths, role, limits; record paths by default instead of copying images.
- `04_generation/api_request_notes.md`: model, size, quality, text-only or image-reference/edit workflow; no API keys.
- `04_generation/images/`: generated images only.
- `05_review/qa_report.md`: style continuity, brief fidelity, text behavior, label correctness, editability checks.
- `05_review/prompt_patches.md`: minimal correction suffixes and reasons.

## Versioning

1. Do not overwrite confirmed `deck_outline.md` or prompt files. For major changes, create a new run folder. For small changes, append `Revision YYYY-MM-DD HH:mm`.
2. If the user rejects the whole direction, create a new run folder and preserve the old one for traceability.
3. `manifest.md` must identify the currently adopted outline, prompts, anchors, and images.
4. Large artifacts and API responses stay in the run folder. Final deliverables may be copied only to the user-specified location or current Codex `outputs/`.
5. Never write secrets, API keys, private tokens, unauthorized source copies, or large cache dumps into the run folder.
