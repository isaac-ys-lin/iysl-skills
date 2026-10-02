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

必填 `chart`、`unit`、`period`、`data`；獨立 SVG 另需 `title` 與 `source`（放在 chart 頁時會沿用頁面標題與 deck 的來源）。
`subtitle` 是一行讀圖說明，`notes` 是頁尾補充，兩者可省略。數字寫成數字、保留原始精度，千分位由工具加。
每種圖的完整例子在 [chart-examples.json](../assets/chart-examples.json)（示意資料，只參考格式）。

## 圖型與資料形狀

前八種在簡報中產生 PowerPoint 原生圖表，其餘嵌入 SVG。

| `chart` | `data` 每列 | 其他欄位 |
| --- | --- | --- |
| `ranking` | `{label, value}` | 可選 `focus`：主角藍、其他灰；依數值排序 |
| `ordered` | `{label, value}` | 保留輸入順序，藍階上色 |
| `trend` | `{label, values}` | `labels`（各期名稱）；多條線時用 `focus` 指定主角 |
| `tracking` | 同 `trend` | 2–4 條，類別色固定 |
| `grouped` | `{label, values}` | `series`（1–4 個序列名） |
| `stacked` | `{label, values}` | `categories`（2–4 類，可再加來源既有的「其他」）；值非負 |
| `sharetrend` | 同 `stacked`，每列一期 | 同 `stacked` |
| `combo` | `{label, value, rate}` | `rateLabel`（比率名稱與單位）；兩軸獨立 |
| `bullet` | `{label, actual, target}` | |
| `waterfall` | `{label, value}` | `start`；可選 `end`（會核對加總）、`focus`、`startLabel`、`endLabel` |
| `dumbbell` | `{label, before, after}` | 可選 `beforeLabel`、`afterLabel` |
| `heatmap` | `{label, values}` | `labels`（各欄名稱） |
| `funnel` | `{label, value}` | 首段大於 0 |
| `waffle` | `{label, value}` | 整數百分點，合計 100 |
| `mekko` | 同 `stacked` | 同 `stacked` |
| `pareto` | `{label, value}` | 非負件數 |
| `indexed` | 同 `trend` | 各序列首期大於 0 |
| `tornado` | `{label, low, high}`，可選 `lowLabel`、`highLabel` | `baseline`（每列的 low ≤ baseline ≤ high）；可選 `model`、`assumptions` 寫進頁尾 |
| `scatter` | `{label, x, y}` | `xLabel`、`yLabel` |
| `box` | `{label, low, q1, median, q3, high}`，可選 `outliers` | |
| `histogram` | `data` 是原始觀察值的數字陣列 | `binWidth`，可選 `binStart` |
| `matrix` | `{label, x, y}` | `xLabel`、`yLabel`、`xDomain`、`yDomain`、`xThreshold`、`yThreshold`；可選 `rubric`、`quadrantLabels`、`highlightedQuadrant` |
| `table` | `{label, value}` | 簡報中改用 `table` 版型 |

缺值寫 `null`：長條保留該列並註明，折線斷開並在頁尾列出缺的期間。零照實寫 `0`。

## 跨圖一致

- 同份簡報追蹤相同類別時，在 `stacked`、`sharetrend`、`grouped`、`tracking`、`waffle`、`mekko`
  填同一份 `categoryDomain`（例如 `["壽險","醫療","意外"]`），顏色就不會因排列或缺類而換掉。
- `trend`、`tracking`、`box`、`scatter` 可用 `yDomain: [下界, 上界]` 指定縱軸，須涵蓋所有值；
  長條一律從零起。

## 獨立 SVG 的尺寸

預設畫布 1200×800。放進 Word 或簡報時填 `layout: "document"`（840×720）或 `"slide"`（960×540）；
`width`、`height` 可調整比例。再填實際置入寬度 `placementWidthInches`，工具會換算字級，
換算後太小（文件 9 pt、簡報 16 pt 以下）時 `WARN`。
每張圖交付輸入 JSON 與 SVG；重製需要完整的 `scripts` 目錄。
