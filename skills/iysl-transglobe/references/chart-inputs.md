# 圖表 spec

同一份 spec 有兩個用途：放在 `deck.json` 的 chart 頁，或交給 SVG renderer 產生獨立圖檔。

```sh
node "$SKILL_DIR/scripts/render-chart.js" input.json chart.svg
```

```json
{
  "chart": "waterfall",
  "title": "案件數由 120 件淨增至 128 件",
  "subtitle": "總量與增減共用零基準；虛線連接每步餘額",
  "unit": "件",
  "period": "2026 Q1",
  "source": "營運資料",
  "notes": ["各原因可相加，沒有重複計算"],
  "start": 120,
  "data": [{"label":"新增","value":24},{"label":"結案","value":-16}]
}
```

獨立 SVG 必填 `chart`、`title`、`unit`、`period`、`source`、`notes`（無註解時 `[]`）與 `data`；
放在 chart 頁時 `title`、`source`、`notes` 可省略。數字寫成數字、保留原始精度，千分位由工具加。
完整例子在 [chart-examples.json](../assets/chart-examples.json)（示意資料，只參考格式）。

## 圖型與資料形狀

前八種在簡報中產生 PowerPoint 原生圖表，其餘嵌入 SVG。

| `chart` | 回答的問題 | `data` 每列 | 備註 |
| --- | --- | --- | --- |
| `ranking` | 誰高誰低 | `{label, value}` | 依數值排序；`focus` 可選，指定時主角藍、其他灰 |
| `ordered` | 有順序的等級或區間 | `{label, value}` | 保留輸入順序，藍階上色 |
| `trend` | 一條主線隨時間的變化 | `{label, values}`，另有 `labels` | `focus` 指定主角序列；只有一條時可省略 |
| `tracking` | 2–4 個固定類別各期變化 | 同 `trend` | 類別色固定 |
| `grouped` | 項目在 2–4 個序列（年度、情境）下的大小 | `{label, values}`，另有 `series` | |
| `stacked` | 各群的內部組成 | `{label, values}`，另有 `categories` | 2–4 類，第五類只能是既有的「其他」；值非負 |
| `sharetrend` | 組成隨期間變化 | 同 `stacked`，每列一期 | |
| `combo` | 金額與比率一起看 | `{label, value, rate}`，另有 `rateLabel`（含單位） | 兩軸獨立 |
| `waterfall` | 期初加減到期末 | `{label, value}`，另有 `start`、可選 `end`、`focus` | 各項可加總 |
| `dumbbell` | 同一項目前後差多少 | `{label, before, after}` | 可設 `beforeLabel`／`afterLabel` |
| `bullet` | 實際與目標 | `{label, actual, target}` | |
| `heatmap` | 兩個維度交叉的強弱 | `{label, values}`，另有 `labels` | 最多 10×12 |
| `funnel` | 同一批對象在哪一階段流失 | `{label, value}`，另有 `sameCohort: true` | 數值不可增加 |
| `waffle` | 單一整體的占比 | `{label, value}` | 整數百分點，合計 100 |
| `mekko` | 規模與組成同時比較 | 同 `stacked` | |
| `pareto` | 少數原因是否占多數 | `{label, value}` | 原因互斥 |
| `indexed` | 起點不同的相對成長 | 同 `trend` | 首期須大於 0 |
| `tornado` | 哪個假設最影響結果 | `{label, low, high}`，另有 `baseline`、`model`、`assumptions` | 來自已算好的模型 |
| `scatter` | 兩個指標的關係 | `{label, x, y}`，另有 `xLabel`、`yLabel` | 3–6 點 |
| `box` | 分布與中位數 | `{label, low, q1, median, q3, high, whiskerRule: "1.5IQR", outliers}` | 需要真實分位數 |
| `histogram` | 原始觀察值的分布 | `data` 為數字陣列，另有 `binWidth` | 10 筆以上 |
| `matrix` | 兩個評分維度的優先序 | `{label, x, y}`，另有 `xLabel`、`yLabel`、`xDomain`、`yDomain`、`xThreshold`、`yThreshold`、`rubric` | 評分定義來自來源 |
| `table` | 單欄數值清單 | `{label, value}` | 簡報中改用 `table` 版型 |

缺值寫 `null`：長條保留該列並註明，折線斷開並在頁尾列出缺的期間。
零是觀察值，不是缺值。

## 跨圖一致

- 同份簡報追蹤相同類別時，在 `stacked`、`sharetrend`、`grouped`、`tracking`、`waffle`、`mekko`
  填同一份 `categoryDomain`（例如 `["壽險","醫療","意外"]`），顏色就不會因排列或缺類而換掉。
- `trend`、`tracking`、`box`、`scatter` 可用 `yDomain: [下界, 上界]` 指定縱軸，須涵蓋所有值；
  長條一律從零起。

## 獨立 SVG 的尺寸

預設畫布 1200×800。放進 Word 或簡報時填 `layout: "document"`（840×720）或 `"slide"`（960×540），
並填實際置入寬度 `placementWidthInches`；工具會檢查換算後的字級（文件 9 pt、簡報 16 pt 以上），
太小時改排版或拆圖，不要縮字。`width`、`height` 可調整比例。
每張圖交付輸入 JSON 與 SVG；重製需要完整的 `scripts` 目錄。
