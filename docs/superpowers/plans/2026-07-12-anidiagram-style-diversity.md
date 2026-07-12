# iysl-anidiagram Style Diversity

Status: Complete
Last updated: 2026-07-12

## Goal

讓同一個 skill 產出的風格、顏色與構圖能依內容發散，不回落到單一淡藍 editorial house，也不把新的風格參考變成固定模板菜單。

## Current contract

- In scope: 完成 Claude 中斷的 `examples/style-range/` showcase；把視覺外觀與空間構圖拆成可檢查的發散條件；補防腐測試、文件與完整驗證。
- Out of scope: 不加入新的 runtime 依賴、不改 SVG renderer、不建立自動套版器、不處理無縫循環或 pipeline 成本分級。
- Acceptance criteria: 三個 style-range SVG 都通過 `render_svg.py --check`；候選案必須至少同時跨一個 visual axis 與一個 spatial axis；style-range 有自動探索與 render 測試；skill-level tests 與 repo verifier 通過；沒有新增快取或背景程序殘餘。

## Decisions

- **Confirmed** — 強模型不需要幾何 helper；本次優化重點是避免風格、顏色與構圖千篇一律。
- **Confirmed** — style directions 是校準跳板，不是八選一菜單；風格需由內容情緒推導。
- **Confirmed** — 可參考 GitHub 原始專案補強判斷邏輯，但 repo examples 維持原創、repo-owned，不引入外部 runtime。
- **Assumed** — 「Claude 做到一半，現在換你」授權完成同一批未提交的 anidiagram style-diversity 修改與驗證，不包含 commit 或 push。

## Implementation outline

- 將 composition 拆成獨立 spatial divergence axes，避免只換色與字體。
- 讓 Creative 與 Review 都驗證 visual + spatial 兩類差異。
- 完成 style-range showcase 說明並新增防腐測試。
- 跑 render、pytest、repo verify、diff/hygiene 檢查與 adversarial review。

## Progress and evidence

- Claude 已新增 `references/style-directions.md`，並接入 `SKILL.md` 與 `svg-authoring.md`。
- `examples/style-range/` 已有 editorial、blueprint、print 三組 SVG/PNG 與 machine-readable fingerprints；2026-07-12 目視確認三組在明度、字感、finish 與空間重心上可明顯辨識。
- Creative 與 Review 已一致要求至少一個 visual axis 加一個 spatial axis；multi-diagram run 會把上一張 accepted fingerprint/poster 帶進 final selection gate。
- Calibration family 改為先獨立推導 fingerprint、後做 range check；若接近 anchor，必須同時說明 visual 與 spatial mutation。
- `test_style_range_examples.py` 會檢查 fingerprint、pairwise poster distance、tracked poster freshness，且 browser/render 缺失會失敗而非 skip。
- `python3 -m pytest ... test_style_range_examples.py`（sandbox 外真實 Chromium）為 `5 passed`；`tools/verify-skill.sh iysl-anidiagram` 為 `25 passed`；`tests/test_package_contract.py` 為 `7 passed`。
- 三個 SVG 另逐一執行 `render_svg.py --check --fps 10`，皆 exit 0；editorial、blueprint、print 的 MP4 均為 2400×1760、10 秒。
- Reviewer re-review 為 clean，先前四個 blockers（假綠、showcase 同質、跨輪重複、八模板退化）均已關閉。
- 清除 `__pycache__` / `.pyc` 後 package residue 檢查為空；未 commit、未 push。
