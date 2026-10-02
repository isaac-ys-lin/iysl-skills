# 版型與 deck.json

`build-deck.js` 讀一份 `deck.json`，依原型簡報（簡報樣板，1920×1080）的版面產生 16:9 PPTX。
完整可建置的例子是 [`assets/example-deck.json`](../assets/example-deck.json)，九頁對應原型的九頁正式內容；
寫新簡報時先看它的密度。

## 結構

```json
{
  "title": "簡報名稱（寫進檔案屬性）",
  "source": "預設資料來源，chart 頁沒填 source 時使用",
  "logo": "可選：使用者提供的官方 Logo 檔路徑，相對於 deck.json",
  "pages": [ { "layout": "cover", "...": "..." } ]
}
```

每頁共用欄位：

| 欄位 | 說明 |
| --- | --- |
| `layout` | 版型名稱，見下表 |
| `eyebrow` | 標題上方的小字：章節編號與主題，例如 `"02　通路表現"`、`"EXECUTIVE SUMMARY"` |
| `title` | 這頁的判斷。一行最好，最多兩行（約 30 個全形字一行） |
| `lede` | 標題下一行：指標、範圍、期間、單位，例如 `"四大通路 FYP 年增率・2026 H1・%"` |
| `footer` | 字串陣列：資料來源、定義、限制。每頁 1–3 行 |
| `speakerNotes` | 講者備忘稿：原稿中這頁的講述內容放這裡 |
| `exhibit` | `chart`、`table`、`compare`、`list` 會自動編 EXHIBIT 號；填 `false` 取消，填 `true` 加給其他版型 |

文字中的 `\n` 是換行。頁碼自動產生（封面不編）。

## 各版型

**cover**：`title`（可用 `\n` 分兩行）、`eyebrow`（會議或場合）、`summary`（一句主訊息）、
`tag`（右上角英文小字，例如 `MANAGEMENT REVIEW`）、`meta`（最多三項 `{label, value}`：提報單位、日期、文件性質）。

**summary**：`thesis` = `{label, heading, body}`，左欄的建議；`evidence` 是 1–4 列
`{value, unit, heading, body}`，右欄的支撐數字。每列的 `body` 寫一行。
`evidence` 放稿子裡真正支撐建議的數字；稿子沒有這類數字時，摘要頁改用 `columns` 或 `flow`。

**kpi**：`main` = `{label, value, unit, benchmarks: [{label, value, unit}]}`，左側大數字與 1–3 個對照；
`secondary` 是 0–4 個 `{label, value, unit}` 次要指標。數字用字串寫出要顯示的樣子（`"+2.4"`、`"−7.8"`）。

**chart**：`chart` 是圖表 spec（見[圖表輸入](chart-inputs.md)）。`title` 與 `source` 可省略，
會用頁面標題與 deck 的 `source`；`unit`、`period`、`data` 必填。`lede` 沒填時用 `chart.subtitle`。
`footer` 沒填時自動列出單位、期間、來源、`notes` 與缺值說明；自己填 `footer` 時記得放進這些。
`aside` = `{label, value, unit, body}` 在圖右側放一個重點數字與兩三行解讀。
`"svg": true` 讓原生圖型改用 SVG 嵌入。

**table**：`columns` 是欄名字串或 `{label, width, align}`（`width` 為相對寬度）；`rows` 是字串陣列，
每列欄數相同，數字照要顯示的格式寫（`"1,284"`）。純數字欄自動靠右。`highlight` 是要強調的列索引（從 0 起），一列寫數字，多列寫陣列（`[0, 2]`）。
一頁約放 9–10 列；更多時只放和標題有關的列，完整表放附錄頁。

**compare**：`options` 是 2–4 個 `{label, name}`（如 `{"label": "PLAN B・建議", "name": "招募與留存"}`）；
`rows` 是 `{label, values}`，`values` 與 `options` 一一對應；`recommended` 是建議方案的索引。
只放能區分方案的比較項目，通常 4–6 列。

**list**：`items` 是 2–5 個 `{tag, heading, body, note}`。`tag` 是左欄短標（「優先查核」），
`note` 是右欄補充（「查核：…」），兩者可省略。`focus` 是要用藍色強調的項目索引。

**columns**：`items` 是 2–4 個 `{kicker, value, unit, heading, body}`；`kicker` 是小標，
`value`／`unit` 是可選的大數字。`focus` 指定強調欄；不填時每欄同重。

**process**：`steps` 是 3–6 個 `{label, heading, body}`；`label` 是日期或步驟名（省略時用 01、02…）。
`focus` 標出目前所在的步驟；不填時全部同色。

**flow**：`nodes` 是 2–5 個 `{label, heading, body}` 方框，由左到右；`connectors` 是方框之間的符號
（預設 `→`，可用 `+`、`=`）；`focus` 是填滿藍色的方框，預設最後一個（通常是結論或本案的回應）；
`note` 是方框下方一行補充。用在「A 加 B 造成 C，所以做 D」這類因果或問題與回應。

**decisions**：深色結尾頁。`items` 是 1–5 個 `{heading, owner, deadline}`。

**chapter**：深色章節頁，`number`、`title`、`summary`。適合 15 頁以上、分成幾個章節的簡報。
