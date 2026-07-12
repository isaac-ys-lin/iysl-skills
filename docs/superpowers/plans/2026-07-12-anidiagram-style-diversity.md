# iysl-anidiagram Style Diversity

Status: Ready
Last updated: 2026-07-13

## Goal

讓同一個 skill 產出的風格、顏色與構圖能依內容發散，不回落到單一淡藍 editorial house，也不把新的風格參考變成固定模板菜單。

## Current contract

- In scope: 保留已完成的 style-diversity 合約；完成 motion craft 合約與 SVG retrofit；修正 renderer paint 同步、spline validation、尾端循環與 verifier 假綠；補 regression tests；隔離驗證後 commit、push 並整合回 `main`。
- Out of scope: 不加入新的 runtime 依賴、不建立自動套版器、不處理 pipeline 成本分級；不納入同時存在的 `iysl-ytdlp-html-report`、README 與 package-contract WIP。
- Acceptance criteria: motion regression tests 能在舊行為失敗並在修正後通過；所有 anidiagram SVG 通過結構、循環與 render gates；平行 render 不再產生不同 frame stream 或 hang；skill/package/release verifier 在隔離 worktree 通過；目標 commits 推送並 fast-forward 整合到遠端 `main`；沒有新增快取或背景程序殘餘。

## Decisions

- **Confirmed** — 強模型不需要幾何 helper；本次優化重點是避免風格、顏色與構圖千篇一律。
- **Confirmed** — style directions 是校準跳板，不是八選一菜單；風格需由內容情緒推導。
- **Confirmed** — 可參考 GitHub 原始專案補強判斷邏輯，但 repo examples 維持原創、repo-owned，不引入外部 runtime。
- **Assumed** — 「Claude 做到一半，現在換你」授權完成同一批未提交的 anidiagram style-diversity 修改與驗證，不包含 commit 或 push。
- **Confirmed** — 2026-07-13 使用者授權修正 review findings、commit、push，並把成果整合回 `main`。
- **Confirmed** — Motion easing 必須依動作語義選擇，不以單一 ease-out 曲線全域替換。
- **Confirmed** — 無關的 ytdlp skill 與 package inventory WIP 必須留在原 worktree，不得被 staging、commit 或 merge 帶入。

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
- `312d74d` 與 `0d78f9c` 已提交。2026-07-13 deep review 重現的 motion、renderer、verifier、loop 與 active-content blockers 均有先 RED 後 GREEN 的 regression guard；最終 adversarial re-review 為 clean。
- Fresh detached worktree：root verifier regression `2 passed`、package contract `8 passed`、anidiagram `58 passed`、clarify `5 passed`、sync `8 passed`，`tools/verify-release.sh` 回報 `portable release gates passed`。
- Packaged install surface：`tools/verify-npx-install.sh` 以 `skills@1.5.16` 在隔離 HOME 安裝四個 skills，source parity 通過且無 cache/noise residue。
- 下一步：依 infrastructure/contracts/tests 與 SVG/MP4 retrofit 分批提交，推送 feature branch，fast-forward 整合並推送 `main`；完成後將本 plan 標記 `Complete`。
