# 版型與 deck.json

`build-deck.js` 讀 `deck.json`，依原型簡報的版面產生 16:9 PPTX。完整例子是
[`assets/example-deck.json`](../assets/example-deck.json)（原型九頁），寫新簡報時照它的密度寫。
欄位缺漏或項目數超出版型時，`build-deck.js` 會指出是哪一頁、哪個欄位。

```json
{
  "title": "簡報名稱（寫進檔案屬性）",
  "source": "預設資料來源，chart 頁沒填 source 時使用",
  "logo": "可選：使用者提供的官方 Logo 檔路徑，相對於 deck.json",
  "pages": [ { "layout": "cover", "...": "..." } ]
}
```

## 每頁共用欄位

- `eyebrow`：標題上方小字，章節編號與主題（`"02　通路表現"`）。
- `title`：這頁的判斷，一行最好。
- `lede`：標題下一行，寫指標、範圍、期間、單位（`"四大通路 FYP 年增率・2026 H1・%"`）。
- `footer`：字串陣列，寫來源、定義、限制。
- `speakerNotes`：原稿中這頁的講述內容。
- `exhibit`：`chart`、`table`、`compare`、`list` 自動編號；`false` 取消，`true` 加給其他版型。

文字中的 `\n` 是換行；頁碼自動產生。

## 從稿子到版型

| 稿子裡的內容 | `layout` | 主要欄位 |
| --- | --- | --- |
| 開場 | `cover` | `title`、`eyebrow`、`summary`、`tag`、`meta: [{label, value}]` |
| 一段話的建議與理由 | `summary` | `thesis: {label, heading, body}`、`evidence: [{value, unit, heading, body}]` |
| 一個核心數字和它的對照（同業、目標、去年） | `kpi` | `main: {label, value, unit, benchmarks}`、`secondary` |
| 幾個項目的高低、時間變化、組成 | `chart` | `chart`（[圖表 spec](chart-inputs.md)）、`aside: {label, value, unit, body}` |
| 排名或需要逐項查的數字 | `table` | `columns`（字串或 `{label, width, align}`）、`rows`、`highlight` |
| 「方案一、方案二」 | `compare` | `options: [{label, name}]`、`rows: [{label, values}]`、`recommended` |
| 「原因有三」「風險包括」「下一步要」（有順序） | `list` | `items: [{tag, heading, body, note}]`、`focus` |
| 並列重點，可帶數字 | `columns` | `items: [{kicker, value, unit, heading, body}]`、`focus` |
| 時程、流程、上線步驟 | `process` | `steps: [{label, heading, body}]`、`focus`（目前所在步驟） |
| 「因為…所以…」、問題與解法 | `flow` | `nodes: [{label, heading, body}]`、`connectors`（`→`、`+`、`=`）、`focus`、`note` |
| 需要聽眾決定或核准的事 | `decisions` | `items: [{heading, owner, deadline}]` |
| 15 頁以上的章節分隔 | `chapter` | `number`、`title`、`summary` |

## 工具查不到的取捨

- `summary` 的 `evidence` 放真正支撐建議的數字；稿子沒有這類數字時改用 `columns` 或 `flow`，
  不用「3 項」「12 月」這類計數或日期湊數。
- `kpi`、`table` 的數字寫成要顯示的字串（`"+2.4"`、`"1,284"`）。
- `chart` 頁沒填 `footer` 時自動列出單位、期間、來源與缺值；自己填時要包含這些。
- `table` 只放和標題有關的列，完整表放附錄頁；`compare` 只放能區分方案的列。
- `flow` 的 `focus` 預設最後一個方框，通常是結論或本案的回應。
- 口語鋪陳、例子與轉場留在 `speakerNotes`，頁面上只放結論與證據。
