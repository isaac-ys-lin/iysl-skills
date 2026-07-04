---
name: iysl-deck-ab
description: 使用 $iysl-deck-ab 將任意內容、講稿、producer notes、slide brief 或 image prompt set 轉成 source-faithful deck outline、slide briefs、Mode A/B prompts 與 reference-image style-anchor workflow。觸發：iysl-deck-ab、STYLE_INSTRUCTIONS、SOURCE NEEDED、visible-label whitelist、中文 visible labels、風格不一致、style anchor、A/B 生圖 prompt、API production prompt pack。排除：直接 PPTX/Keynote export、單張圖片生成、純潤稿、純素材搜尋、純設計審查。
---

# iysl-deck-ab

## Job Boundary

`$iysl-deck-ab` produces source-faithful deck outlines, slide briefs, Mode A/B prompts, and style anchors. Use it for:

- source material, talks, producer notes, or briefs -> deck outline / slide briefs
- existing slide brief or image prompt set -> Mode A/B image-generation prompts
- multi-slide generation drift -> reference-image / style-anchor workflow

Do not invent facts. Mark gaps as `SOURCE NEEDED`.

## Near-Neighbor Exclusions

Exclude PPTX/Keynote export, one-off image generation, writing polish, asset search, and design critique only.

## Core Flow

1. Classify input: raw source, transcript, brief, slide brief, prompt set, or critique.
2. Load `references/core-role.md` and adopt it as the working role and output contract for all outline and prompt production, whether working inline or via subagent.
3. For raw source/deck needs, load `references/deck-outline-contract.md` and outline first.
4. For A/B prompts, style anchors, API packs, or slide briefs, load `references/image-prompt-workflow.md`.
5. Before saving artifacts, load `references/artifact-storage.md`.
6. Keep outline as story truth; prompts are visual-generation instructions.

## Reference Loading Map

- `references/core-role.md`: role and output contract for inline or subagent work.
- `references/deck-outline-contract.md`: STYLE_INSTRUCTIONS, Slide 1..N, source fidelity, cover/back-cover, Chinese labels.
- `references/image-prompt-workflow.md`: Mode A/B, whitelist, assembly, API/reference anchor, checks, correction suffix.
- `references/artifact-storage.md`: run folder, manifest, staged folders, versioning, secrets ban.
- `evals/`: routing regression cases.

## Subagent Rule

Use a subagent for long outlines, multi-page prompts, or API packs when available. Before dispatch, read `references/core-role.md` and prepend it with source material, target language, label policy, output mode, slide count, anchor needs, and — when known — the audience and the decision the deck must drive. If the user did not specify audience or purpose, infer them from the source and mark the assumption instead of blocking. Main agent validates.

## Run Folder Trigger Summary

Create a run folder for more than 3 slides, subagent work, Mode A/B, API production, style anchors, image generation, or second-round corrections. Prefer the project workspace; otherwise use `work/iysl-deck-ab-runs/`. Never write artifacts into the skill package, `/tmp`, Downloads, or multiple locations.

## Validation Checklist

- One `STYLE_INSTRUCTIONS` block before Slide 1.
- Slide 1 is cover; final slide is back cover; `N <= 20`.
- Every slide has exactly `// NARRATIVE GOAL`, `// KEY CONTENT`, `// VISUAL`, `// LAYOUT`.
- Every `// VISUAL` states a checkable logic spec: element count, order, direction, and relation type.
- Unsupported facts are marked `SOURCE NEEDED`.
- Chinese visible labels stay in Traditional Chinese unless source says otherwise.
- Mode B includes a visible-label whitelist and no extra in-image text.
- Style-anchor instructions inherit visual language only, not anchor content.
