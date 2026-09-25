# SVG 圖表輸入與離線重製

使用隨附工具產出可獨立閱讀的 SVG：

```sh
node "$SKILL_DIR/scripts/render-chart.js" input.json chart.svg
```

程式也可供其他格式工具呼叫：

```js
const { render } = require('./skills/iysl-transglobe/scripts/render-chart');
const svg = render(spec);
```

`$SKILL_DIR` 是已安裝 `iysl-transglobe` skill 的根目錄。每份圖用資料支持的結論作為 `title`，以 `subtitle` 說明圖形編碼、基準或分母；假設與限制放在 `notes`。原型完整案例在 [chart-examples.json](../assets/chart-examples.json)，只讀本次圖型並替換為任務數據；示例不可當成真實資料。每份 `spec` 必填 `chart`、`title`、`unit`、`period`、`source`、`notes`、`data`；無註解時 `notes: []`。可見頁尾與無障礙描述保留解讀所需的中繼資料，SVG 的 `<metadata>` 另存完整原始 spec。預設畫布 1200×800；可用整數 `width`、`height`（500×350 至 10000×20000）指定比例，實際可用尺寸依內容密度而定，嵌入時依 `viewBox` 等比例縮放。

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

| `chart` | 要回答的問題 | `data` 每列形狀 | 重要限制 |
| --- | --- | --- | --- |
| `ranking`、`ordered`、`table` | 項目高低／排序 | `{label,value|null}` | ranking 要 `focus`；缺值保留，不轉零 |
| `bullet` | 實際是否達標 | `{label,actual,target}` | 實際、目標同單位 |
| `heatmap` | 二維強度 | `{label,values:[number|null,...]}`，另有 `labels` | 每列同欄數，1–10×1–12；缺格標示未提供 |
| `trend`、`tracking` | 多序列時間變化 | `{label,values:[number|null,...]}`，另有 `labels` | 每序列同期間；`null` 斷線；不規則時間改表格 |
| `waterfall` | 期初如何走到期末 | `{label,value}`，另有 `start`、可選 `end`/`focus` | 所有變動可加總，`end` 必須驗證相等 |
| `dumbbell` | 前後差異 | `{label,before,after}` | 同一項目、同一口徑 |
| `scatter` | 兩指標關係 | `{label,x,y}` | 3–6 點，過密／重疊改表格或其他散點工具；不推論因果 |
| `box` | 分布與中位數 | `{label,low,q1,median,q3,high,whiskerRule:"1.5IQR",outliers:[]}` | 五數摘要必須排序；鬚端必須是 1.5 IQR 定義的端點，不能拿任意最小／最大值冒充 |
| `funnel` | 階段流失 | `{label,value}`，另有 `sameCohort:true` | 同一母體、非負整數且數值不可增加 |
| `waffle` | 單一整體占比 | `{label,value}` | 整數百分點且總和 100 |
| `stacked` | 群體組成 | `{label,values:[...]}`，另有 `categories` | 每列同類別；數值非負 |
| `indexed` | 相對成長 | 同 `trend` | 每列首值必須大於 0；首期＝100。零或負基期改用 `trend`，並明示不同解讀 |
| `pareto` | 優先原因 | `{label,value}` | 原因互斥、件數非負 |
| `tornado` | 單因子敏感度 | `{label,low,high}`，另有 `baseline`、`model`、`assumptions` | 各結果必須包住 baseline；每次只變一因子 |
| `mekko` | 規模與組成 | 同 `stacked` | 矩形面積代表整體份額 |
| `matrix` | 影響與難度 | `{label,x,y}`，另有 `xLabel`、`yLabel`、domains、thresholds、`rubric` | 軸、分界與評分意義均由來源提供，不能預設 1–5 |

`scatter` 必填有單位的 `xLabel`／`yLabel`；可提供涵蓋全部觀察值的 `xDomain`／`yDomain`，工具會揭露顯示範圍，非零起點需在讀圖說明中交代。直接標籤無法安全排入時才改編號對照；`matrix` 必填 `xDomain`、`yDomain`、`xThreshold`、`yThreshold`；`stacked`／`mekko` 必填 2–4 個 `categories`（第五只能是既有 Other）。超過單圖容量、標籤過長或資料不符合語意時，工具會拒絕產圖；拆圖、改表格或補足資料，不能刪資料、合併類別或臆造缺值。此工具是來源網站 v2.5.1 的本機 SVG 實作，非 Office 原生可編輯圖表；Office 嵌入與動態資料連結另由格式工具負責。

`labels` 必須逐一列出所有欄位／期間。`trend` 必填序列名稱 `focus`；`tracking` 保留 2–4 個固定類別色。時間圖使用等間距格線，先核對順序與頻率；不規則時間可補回來源定義的完整期間並以 `null` 表示缺值，或改用能保留實際時間距離的工具。`dumbbell` 可指定 `beforeLabel`／`afterLabel`，避免把情境比較誤寫為改善前後。

`indexed` 的 `data` 與 `unit` 填原始觀察值和原始單位；工具自行計算首期＝100 的指數，並保留原值。不要先正規化或四捨五入輸入，也不要將金額的單位改寫為指數。
標題點名一個比較主角時，可填 `focus` 為該序列名稱；其他序列保留灰線及可讀數值。未指定時各面板維持相同重量。

## 文件尺寸與資訊層級

依實際容器選 `layout: "document"`（預設 840×720）或 `"slide"`（960×540），
並填 `placementWidthInches` 為最終置入寬度；未指定 layout 時沿用 `"web"`（1200×800）。
例如 Word 寬 6.1 英吋的圖填 `layout: "document", placementWidthInches: 6.1`。
`width`／`height` 仍可重排畫布；不是單純把原圖縮小。

工具用「SVG 字級 × 置入英吋 × 72 ÷ viewBox 寬」核對成品 pt：
文件圖中文字至少 9 pt、來源至少 8 pt；簡報至少 16／12 pt。
這是工具的可讀性下限，閱讀距離較遠時再提高。寬度變動後重製並重驗；
圖高依比例計算，仍須確認容器高度與實際頁面。資料太密時改排版、拆圖或改原生表格。

類別名稱已有固定圖例時，區塊內優先保留比例與原值，共用單位只標一次。
圖面 source 使用讀者能理解的來源名稱；檔案路徑、原始定位等保存在輸入 JSON 的
`sourceReference` 等欄位。影響解讀的期間、分母、限制仍在圖上，完整 spec 仍存於 metadata。
可用圖庫中的「相同數據，不同問題」對照總量、通路內組成及整體份額；
由讀者問題決定圖型，精簡標籤時保留原始資料。

`tornado` 的 `low`／`high` 是模型算好的輸出值，不是任意乘數。每列可提供 `lowLabel`／`highLabel` 保留測試假設（如 -15%／+15%），兩者必須成對；橫軸以基準為中心。工具只畫圖，不替使用者製造模型；將基準、每因子的測試區間和一次只變一項的口徑記在 `model`／`assumptions`。`matrix` 的分界必須在量尺內部；`rubric` 說明來源的評分定義。可提供四個 `quadrantLabels`（左上、右上、左下、右下）與 `highlightedQuadrant`（TL／TR／BL／BR），只用來源或使用者定義的象限意義，不自動推論優先序。

每張圖交付輸入 JSON、SVG，以及完整 `scripts` 目錄（入口會引用同目錄工具），不能只交付入口檔。全部可離線重製；完整有效例子與可產生的預覽在 `tests/render-chart.test.js`、`tests/make-gallery.js`。圖庫示意資料是驗證材料，使用時替換為來源資料。

## 原型校準

本次對照使用者提供的 TransGlobe Blue 原型中 `tools/chart-examples.js`、`tools/mac-layout.js`、`tools/build.js`、`design-tokens.json` 與 `CHART-READABILITY.md`。來源為使用者提供的原型目錄；已將相關繪圖邏輯與完整示例保存在 skill 內，使用時不依賴原作者的本機目錄。

繪圖程式保留可變輸入、缺值和密度檢查；原型固定示例的標題、分母、期間和量尺不能直接套到新資料。標題／主標籤／軸與圖例／來源約 34／20／18／16 px；最終放進 Word 或簡報後仍須查看實際尺寸，密集圖可分圖或放大，不能把字級換算通過稱為已通過閱讀驗收。
