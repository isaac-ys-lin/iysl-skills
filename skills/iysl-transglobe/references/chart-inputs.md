# 選圖與圖表 spec

## 選圖

先寫出標題要說的那一句話，再選能讓讀者一眼看到它的圖：

1. **要不要圖？** 只有一個數字用 `kpi` 版型；要逐項查精確值或項目太多用 `table`；
   沒有數字的並列、流程、選項用 `columns`、`process`、`compare`。
2. **回答什麼問題？** 用下表找圖型。使用者指定且資料適用就照做；沒指定就直接選，交付時用一句話說理由。
3. **資料夠不夠？** 不夠就改用要求較低的圖或表格並說明缺什麼；不補造分母、分布、目標或模型。

- 同一份組成資料：比總量用 `ranking`（加總後），比組成用 `stacked`，兩者都要看用 `mekko`。
- 只有兩個時點、重點是差距用 `dumbbell`；三期以上用 `trend`。
- 類別超過四個又要固定顏色時，拆圖或改表格。
- 一頁一張圖；兩張要對照時拆頁或改用 `grouped`、`combo`。

上色見[設計規範](design-rules.md)；標題點名主角時填 `focus`。

## 圖型

「原生」欄有 ● 的圖型在簡報中產生 PowerPoint 原生圖表，其餘嵌入 SVG。

| `chart` | 回答的問題 | `data` 每列 | 工具查不到、要自己確認的事 | 原生 |
| --- | --- | --- | --- | :-: |
| `ranking` 排行比較 | 同期誰高誰低 | `{label, value}` | 同單位、單一期間 | ● |
| `ordered` 階段與強度 | 有順序的等級或區間 | `{label, value}` | 照來源分級，缺級不補 | ● |
| `trend` 單一趨勢與同業 | 主角與比較對象隨時間的變化 | `{label, values}`＋`labels` | 期間等間距；`focus` 指定主角 | ● |
| `tracking` 跨期追蹤 | 2–4 個固定類別各期變化 | 同 `trend` | 類別跨期一致 | ● |
| `grouped` 多序列分組長條 | 項目在 2–4 個序列（年度、情境）下的大小 | `{label, values}`＋`series` | 同單位 | ● |
| `stacked` 100% 堆疊長條 | 各群的內部組成 | `{label, values}`＋`categories` | 類別互斥；第五類只能是既有的「其他」 | ● |
| `sharetrend` 組成隨期間變化 | 組成如何隨期間移動 | 同 `stacked`，每列一期 | 同 `stacked` | ● |
| `combo` 金額柱＋比率線 | 規模與比率一起看 | `{label, value, rate}`＋`rateLabel`（含單位） | 兩軸獨立，不比高度 | ● |
| `waterfall` 瀑布圖 | 期初加減到期末 | `{label, value}`＋`start`，可選 `end`、`focus` | 各項可相加、不重疊 | |
| `dumbbell` 啞鈴圖 | 同一項目在兩個時點或情境差多少 | `{label, before, after}`，可設 `beforeLabel`／`afterLabel` | 同一項目、同口徑 | |
| `bullet` 實際與目標 | 實際離目標多遠 | `{label, actual, target}` | 目標要有來源 | |
| `heatmap` 二維強度 | 兩個維度交叉的強弱 | `{label, values}`＋`labels` | 各格同口徑 | |
| `funnel` 漏斗圖 | 同一批對象在哪一階段流失 | `{label, value}`＋`sameCohort: true` | 同一母體、同一期間 | |
| `waffle` 百格占比圖 | 單一整體的占比 | `{label, value}` | 部分互斥 | |
| `mekko` Marimekko 市場結構圖 | 規模與組成同時比較 | 同 `stacked` | 共同的整體分母 | |
| `pareto` 帕累托圖 | 少數原因是否占多數 | `{label, value}` | 原因互斥 | |
| `indexed` 指數化小倍數趨勢圖 | 起點不同的相對成長 | 同 `trend` | 共同基期 | |
| `tornado` 敏感度龍捲風圖 | 哪個假設最影響結果 | `{label, low, high}`＋`baseline`、`model`、`assumptions` | 來自一次只改一項的已算好模型 | |
| `scatter` 散點圖 | 兩個指標的關係與例外 | `{label, x, y}`＋`xLabel`、`yLabel` | 不宣稱因果 | |
| `box` 箱型圖 | 分布、中位數與離群值 | `{label, low, q1, median, q3, high, whiskerRule: "1.5IQR", outliers}` | 真實分位數，只有平均不能用 | |
| `histogram` 直方圖 | 原始觀察值的分布 | 數字陣列＋`binWidth` | 組距來自來源或分析計畫 | |
| `matrix` 2×2 優先矩陣 | 兩個評分維度的優先序 | `{label, x, y}`＋`xLabel`、`yLabel`、`xDomain`、`yDomain`、`xThreshold`、`yThreshold`、`rubric` | 評分與門檻來自來源 | |
| `table` 資料表 | 單欄數值清單 | `{label, value}` | 簡報中改用 `table` 版型 | |

## Spec

同一份 spec 可放在 `deck.json` 的 chart 頁，或交給 renderer 產生獨立 SVG：

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

獨立 SVG 必填 `chart`、`title`、`unit`、`period`、`source`、`notes`（可為 `[]`）與 `data`；
放在 chart 頁時 `title`、`source`、`notes` 可省略。數字寫成數字，千分位由工具加。
各圖型的完整例子在 [chart-examples.json](../assets/chart-examples.json)（示意資料，只參考格式）。

- **缺值**寫 `null`：長條保留該列，折線斷開，工具會在頁尾列出。零是觀察值，不是缺值。
- **跨圖同色**：同份文件追蹤相同類別時，填同一份 `categoryDomain`（例如 `["壽險","醫療","意外"]`）。
- **縱軸範圍**：`trend`、`tracking`、`box`、`scatter` 可用 `yDomain: [下界, 上界]`，須涵蓋所有值；長條一律從零起。
- **獨立 SVG 尺寸**：預設 1200×800；放進 Word 或簡報時填 `layout: "document"` 或 `"slide"` 與實際置入寬度
  `placementWidthInches`，工具會檢查換算後的字級。重製需要完整的 `scripts` 目錄。
