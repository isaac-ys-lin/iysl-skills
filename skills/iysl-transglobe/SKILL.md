---
name: iysl-transglobe
description: Turn a text script, outline, meeting notes or report into a finished 全球藍 / TransGlobe (全球人壽) PowerPoint deck with the prototype's page layouts and native, editable charts; also restyle existing PowerPoint, Word, Excel, HTML or SVG to 全球藍, and recommend and render TransGlobe charts from data. Use whenever the user wants a 全球藍 or TransGlobe deck, 簡報, 文字稿／講稿做成簡報, chart or restyle, even when they only paste text and ask to 做成簡報 in a TransGlobe context. Exclude design-system maintenance, generic blue styling, and non-TransGlobe deck outlines or image-prompt decks.
metadata:
  compatibility: PPTX assembly requires Node.js 18 or later and npm (run npm ci once in scripts/); the SVG chart renderer alone needs only Node.js. LibreOffice is optional for page previews.
---

# iysl-transglobe

把文字稿做成全球藍簡報，或把既有檔案套用全球藍。成品的標準是原型簡報
[`assets/example-deck.json`](assets/example-deck.json)：每頁一個判斷、每頁有主視覺、
數字看得到出處、圖表在 PowerPoint 裡可以編輯。

## 原則

原型的製作指南只有四句，照這四句做取捨：

1. **觀點在前，證據在後。** 先給結論頁（主管摘要），再放支撐的數字與圖。
2. **一頁，一個清楚的判斷。** 標題寫結論（「個險是唯一衰退的通路」），不寫主題（「通路表現」）；主題放 eyebrow。
3. **先寫結論，再選最能支持它的圖。** 圖的工作是讓讀者一眼看到標題說的事。
4. **刪減內容優先於縮小字級。** 放不下就拆頁、改成表格或移到講者備忘稿。

資料底線只有這幾條，其餘交給工具檢查：

- 數字只來自使用者給的內容，不估、不補、不改精度；缺值就標「未提供」。
- 單位、期間、分母與來源要在頁面上看得到（lede、圖或頁尾）。
- 標題的判斷要有資料支持；稿子本身的主張照原意寫，不自行加強成因果或預測。
- 工具拒絕或警告時，依訊息改圖型、拆頁或改表格，不刪資料、不合併類別。

## 文字稿 → 簡報

1. **先寫故事線。** 讀完整份稿子，寫下聽眾要帶走的一句話，再列出每頁的一句判斷。
   決策型簡報預設：封面 → 主管摘要 → 證據（KPI、圖、表）→ 診斷或選項 → 決議事項。
   說明型（商品、制度、專案）可用：封面 → 重點摘要 → 重點拆解（columns／list）→ 流程或時程 → 下一步。
   一般稿子做成 6–12 頁；同一個論點不要拆成兩頁重複講。
2. **每頁配一個主視覺。** 有數字就用 KPI 或圖；比較精確數值用表格；選擇題用方案比較；
   步驟或時程用 process；因果或「問題 → 回應」用 flow；並列重點用 columns；有先後順序的原因、風險或行動用 list。
   不做只有條列文字的頁面——那是講者稿，放進 `speakerNotes`。
3. **寫 `deck.json`。** 版型與欄位見 [版型說明](references/page-layouts.md)，完整範例是
   [`assets/example-deck.json`](assets/example-deck.json)；圖表 spec 見[圖表輸入](references/chart-inputs.md)，
   選圖見[選圖指南](references/chart-selection.md)。
4. **建置。** `$SKILL_DIR` 是本 skill 的目錄。

   ```sh
   npm ci --prefix "$SKILL_DIR/scripts"        # 第一次使用時安裝
   node "$SKILL_DIR/scripts/build-deck.js" deck.json deck.pptx
   ```

   `WARN` 代表標題過長、文字可能溢出或表格太長；照訊息精簡或拆頁後重建。
5. **看成品。** 有 LibreOffice 時轉成圖片逐頁看：

   ```sh
   soffice --headless --convert-to pdf deck.pptx && pdftoppm -png -r 60 deck.pdf page
   ```

   檢查標題是否在兩行內、文字有沒有溢出或重疊、圖表標籤是否可讀、頁序是否照故事線。
   LibreOffice 以替代字型顯示，只能檢查版面；沒有預覽工具時，交付時說明未做視覺檢查。
6. **交付** PPTX，並附 `deck.json` 供重製。簡述故事線與頁數、哪些圖是原生圖表、
   哪些是 SVG，以及稿子裡沒有、因此留白或標「未提供」的資料。

## 版型

| `layout` | 用途 | 主要欄位 |
| --- | --- | --- |
| `cover` | 封面 | `title`、`eyebrow`、`summary`、`tag`、`meta` |
| `summary` | 主管摘要：一個建議加 2–3 個支撐數字 | `thesis`、`evidence` |
| `kpi` | 一個主指標，加對照與次要指標 | `main`、`secondary` |
| `chart` | 一張圖回答一個問題，可加旁註大數字 | `chart`、`aside` |
| `table` | 排名或需要精確數值的資料 | `columns`、`rows`、`highlight` |
| `compare` | 方案或選項比較，標出建議方案 | `options`、`rows`、`recommended` |
| `list` | 有優先序的原因、風險或行動（2–5 項） | `items`、`focus` |
| `columns` | 2–4 個並列重點，可帶數字 | `items`、`focus` |
| `process` | 3–6 步的流程或時程 | `steps`、`focus` |
| `flow` | 2–5 個方框的因果或「問題 → 回應」 | `nodes`、`connectors`、`note` |
| `decisions` | 深色結尾頁：要決定或要做的事 | `items` |
| `chapter` | 長簡報的深色章節頁 | `number`、`title`、`summary` |

## 圖表

- `ranking`、`ordered`、`trend`、`tracking`、`grouped`、`stacked`、`sharetrend`、`combo`
  產生 PowerPoint 原生圖表，可在 PowerPoint 裡「編輯資料」；其餘圖型嵌入 SVG 並附 PNG 後備。
  需要保留 SVG 時，在該頁加 `"svg": true`。
- 單獨需要 SVG（HTML、Word、純圖）時：`node "$SKILL_DIR/scripts/render-chart.js" input.json chart.svg`。

## 套用到既有檔案

使用者要改的是既有的 PowerPoint、Word、Excel 或 HTML 時，在副本上改，保留原檔；
讀[格式與驗收](references/formats-and-validation.md)中對應格式的段落。圖表從原生圖表、
內嵌工作簿或來源表格取得數據重畫，只有點陣圖時保留原圖並列出需要的資料。
簡報若需要重寫才能有清楚的判斷，先說明，再把原檔內容當文字稿走上面的流程重建。

色彩、字型與尺寸規則見[設計規範](references/design-rules.md)。
