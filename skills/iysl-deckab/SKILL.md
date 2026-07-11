---
name: iysl-deckab
description: 使用 $iysl-deckab 將任意內容、講稿、producer notes、slide brief 或 image prompt set 轉成 source-faithful deck outline、slide briefs、Mode A/B prompts 與 reference-image style-anchor workflow。觸發：iysl-deckab、STYLE_INSTRUCTIONS、SOURCE NEEDED、visible-label whitelist、中文 visible labels、風格不一致、style anchor、A/B 生圖 prompt、API production prompt pack。排除：直接 PPTX/Keynote export、單張圖片生成、純潤稿、純素材搜尋、純設計審查。
---

# iysl-deckab

## Job Boundary

`$iysl-deckab` produces source-faithful deck outlines, slide briefs, Mode A/B prompts, and style anchors. Use it for:

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
4. Style divergence（outline 工作必經）：dispatch 前，主 agent 先依主題與 producer notes 向使用者提出**至少三個明顯不同**的風格方案。每案包含：方案名稱、design aesthetic、背景色與色票（hex）、字體氣質、visual elements 語言、一句為何適合本內容。三案的差異必須一眼可辨——想像三張 cover 縮圖並排，若任兩張會被認成同一套 deck，重新生成。採用正題/反題/wildcard 結構：
   - **正題**：最符合題材直覺期待的方向，把該方向做到最高水準。
   - **反題**：刻意與正題在核心維度上完全相反（暗↔亮、密↔疏、冷↔暖、technical↔humanist、克制↔張揚），風格大膽，但理由必須嚴謹——從內容的邏輯或情緒論證為什麼反轉反而更能表達這份素材，不是為了大膽而大膽。禁止安全折衷：反題若看起來只是正題的變奏，即為不合格。
   - **Wildcard**：從 source 的內容隱喻推導出的方向，不落在常見 family 清單內。
   三案在明度基調、色彩策略、字體氣質、圖像策略中至少兩個維度上彼此不同（維度定義見 `core-role.md` Phase 1）。等使用者選擇、混搭或調整後，把選定方向作為 dispatch 的 style direction。跳過條件：使用者已明確指定視覺風格、已提供 style anchor、或明確要求直接產出；不可互動（batch/自動化）時自選一案並在交付說明中標注理由。
5. For A/B prompts, style anchors, API packs, or slide briefs, load `references/image-prompt-workflow.md`.
6. Before saving artifacts, load `references/artifact-storage.md`.
7. Keep outline as story truth; prompts are visual-generation instructions.

## Reference Loading Map

- `references/core-role.md`: authoritative role, STYLE_INSTRUCTIONS definition, slide structure, constraints, and language rules.
- `references/deck-outline-contract.md`: input classification and outline-specific supplements (references core-role.md for shared definitions).
- `references/image-prompt-workflow.md`: Mode A/B, whitelist, assembly, API/reference anchor, checks, correction suffix.
- `references/artifact-storage.md`: run folder, manifest, staged folders, versioning, secrets ban.
- `evals/`: routing regression cases.

## Execution Model

**預設走 subagent。** 所有 outline、A/B prompt、API pack 生產工作都派給 subagent 執行。主 agent 負責：分類輸入 → 讀取 references → 組裝 dispatch prompt → 派發 subagent → 用 Validation Checklist 驗收產出。

主 agent 只在以下情況 inline 處理：單張 slide 的小修正、prompt patch、或使用者明確要求不用 subagent。

## Subagent Dispatch

`references/core-role.md` 是 subagent 的完整 role prompt 與 output contract。派發時，在 `core-role.md` 後附上：

1. 完整 source material
2. Target language 與 label policy
3. Output mode（outline / Mode A / Mode B / API pack）
4. Slide count 上限（若使用者未指定，由主 agent 依素材量建議）
5. Anchor 需求（若有）
6. Audience 與 deck 要驅動的決策（若使用者未指定，標注「由 source 推斷」，不要 block）
7. 選定的 style direction：
   - Outline 模式：用 style divergence 選定或使用者指定的方向；皆無時標注「由 subagent 依內容自選，避免慣用預設」。
   - Mode A/B、API pack、slide brief 模式：一律沿用既有 `STYLE_INSTRUCTIONS`，不重選風格，除非使用者明確要求 restyle。
   - 若因 style anchor 跳過 divergence：主 agent 先從 anchor 萃取 style contract（色彩比例、線寬、留白密度、圖示與標籤樣式）作為 style direction，驗收時檢查 anchor fidelity。
   - 使用者混搭多案時：主 agent 先 normalize 成單一 style direction block（鎖定 palette hex、字體氣質、visual elements 語言、明確排除項），dispatch 與驗收都以此 block 為準。

若需要 `deck-outline-contract.md` 或 `image-prompt-workflow.md` 的補充規則，一併附在 dispatch prompt 中。Subagent 不需要自己載入 references。

## Run Folder Trigger Summary

Create a run folder for more than 3 slides, subagent work, Mode A/B, API production, style anchors, image generation, or second-round corrections. Prefer the project workspace; otherwise use `work/iysl-deckab-runs/`. Never write artifacts into the skill package, `/tmp`, Downloads, or multiple locations.

## Validation Checklist

- One `STYLE_INSTRUCTIONS` block before Slide 1.
- `STYLE_INSTRUCTIONS` faithfully expands the chosen style direction (when one was selected via style divergence).
- Slide 1 is cover; final slide is back cover; `N <= 20`.
- Every slide has exactly `// NARRATIVE GOAL`, `// KEY CONTENT`, `// VISUAL`, `// LAYOUT`.
- Every `// VISUAL` states a checkable spec appropriate to its form: diagram pages give element count, order, direction, and relation type; editorial/full-bleed/typographic pages give focal elements, hierarchy or reading path, and concept-to-visual mapping.
- Visual variety: no visual form repeats on more than two consecutive slides; decks with 6+ content slides mix at least three visual forms.
- Unsupported facts are marked `SOURCE NEEDED`.
- Chinese visible labels stay in Traditional Chinese unless source says otherwise.
- Mode B includes a visible-label whitelist and no extra in-image text.
- Style-anchor instructions inherit visual language only, not anchor content.
