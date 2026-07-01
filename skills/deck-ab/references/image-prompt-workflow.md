# Image Prompt Workflow

## Contents

- Contract and core rules
- Mode A/B suffixes
- Prompt assembly
- Reference anchor workflow
- Result checks and correction suffixes

## Contract

Use this contract when converting a deck outline, slide brief, or image prompt set into Mode A/B slide image prompts, API production prompt packs, or reference-image/style-anchor workflows.

## Core Rules

1. Preserve the original brief. Unless explicitly asked, do not rewrite, translate, summarize, or remove `KEY CONTENT`, `VISUAL`, or `LAYOUT`.
2. Every prompt starts with the complete original style instructions, not only `VISUAL`.
3. Prefer the slide's own language. Chinese slides use Chinese prompt language; English is reserved for tool/API notes where useful.
4. In-image labels preserve original language. Do not translate Chinese visible labels into English.
5. Control instructions are short suffixes after the brief; treat them as removable run configuration.
6. Iterate with minimal prompt patches. Fix the failing element instead of rewriting the whole slide.
7. For production multi-slide generation, use the same style instructions plus the same confirmed reference image/style anchor when the API/tool supports it.
8. Generate each slide independently; consistency comes from repeated style contract and anchor, not a giant combined prompt.

## Mode A

Use Mode A to test complete slide direction, full visual composition, and whether concise in-slide text works.

Mode A suffix:

```text
本次輸出文字策略：模式 A，完整圖文測試。可依照 KEY CONTENT 生成投影片文字，但請保持文字清晰、少量、版面乾淨，不要塞滿。保留原始設計稿中的主要標題、關鍵短句與必要標籤。不要新增不在原稿中的裝飾性文字、假字或無關英文。
```

## Mode B

Use Mode B when PowerPoint, Keynote, HTML, or later layout needs clean editable text.

Mode B suffix template:

```text
本次輸出文字策略：模式 B，短標籤可編輯測試。圖中只能出現以下文字：<白名單文字，以頓號分隔>。不要生成其他文字，不要生成標題、註記、完整句子、假字、英文或多餘圖例。標題、長句與說明文字請保留乾淨留白，供後製排版。
```

The Mode B whitelist comes only from `VISUAL` and necessary diagram labels. Include structural labels only when they help the graphic, such as flow labels, layer names, or axis labels. Titles, long sentences, notes, and explanations stay out of the image for later editing.

## Prompt Assembly

Assemble prompts in this order:

```text
<task framing, such as 16:9 slide visual and target language>

<complete original style instructions>

<complete original target slide brief>

<Mode A or Mode B suffix>

<optional minimal correction from previous result>
```

For anchor-based API calls, attach the anchor image outside the text prompt when supported. Keep this sentence in the prompt:

```text
參考圖用途：只繼承整體視覺語彙、色彩比例、線寬、留白密度、圖示風格與標籤樣式；不要複製參考圖的構圖、內容、文字或 slide 主題。
```

Keep API parameters separate from the creative prompt. Typical high-quality settings:

```text
model: gpt-image-2
size: 2048x1152
quality: high
output_format: png
```

Use 3840x2160 only after visual direction is confirmed, because it costs more and may be slower.

## Reference Anchor Workflow

Use this workflow when the user prepares multi-slide production generation or reports inconsistent style.

1. Select one or two confirmed style anchors from prior outputs or user-provided references.
2. Record anchor file paths. Do not copy images unless required.
3. Assign roles if two anchors are used, such as `primary style anchor` and `secondary diagram-density anchor`.
4. Generate each slide independently; do not create all slides on one canvas unless the user asks for a contact sheet.
5. If supported, use image-reference or edit workflow rather than text-only generation.
6. Repeat the complete style instructions, anchor-role sentence, target slide brief, and Mode A/B suffix for every slide.
7. Anchor instructions must be narrow: inherit visual language only, not content, layout, slide number, labels, or topic.
8. Explain that text-only style locks are weaker when no real image reference is available.

Suggested anchor suffix:

```text
參考圖一致性策略：請以隨附參考圖作為全套投影片的 style anchor，只繼承平面向量資訊圖語彙、暖白背景、海軍藍/赤土橘/灰藍色彩比例、細線條、低陰影、留白密度、outline icon 風格與短中文標籤樣式。不要複製參考圖的構圖、主題、文字、節點數量或內容。此頁仍需依照下方 Slide brief 重新生成。
```

Avoid weak strategies: one giant prompt for all slides, `n` variants from one prompt for different slides, multi-turn context as the only consistency control, or drifting into 3D/photorealistic/UI-template styles unless the source brief asks for it.

## Result Checks

Check in order:

1. Source fidelity: unsupported facts remain `SOURCE NEEDED`.
2. Style continuity: color, whitespace, tone, and visual system follow the style block.
3. Brief fidelity: visual and layout match the slide brief.
4. Text behavior: Mode A has limited clean key text; Mode B obeys the whitelist.
5. Label correctness: Chinese characters and acronyms are exact.
6. Editability: final text can be added later in a clear area.

When a result fails, report the smallest useful correction suffix, for example:

- `補充：責任必須是一條獨立的淡赤土色曲線，不只是背景面積。`
- `補充：白名單外文字全部移除，使用無字圖例符號表示層級。`
- `補充：四字以上標籤改由後製疊字，圖中只保留無字圖例。`
- `補充：此頁成效數字標 SOURCE NEEDED，不以推測數字代替。`
