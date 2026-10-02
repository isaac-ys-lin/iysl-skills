---
name: iysl-transglobe
description: Turn a text script, outline, meeting notes or report into a finished 全球藍 / TransGlobe (全球人壽) PowerPoint deck with the prototype's page layouts and native, editable charts; also restyle existing PowerPoint, Word, Excel, HTML or SVG to 全球藍, and recommend and render TransGlobe charts from data. Use whenever the user wants a 全球藍 or TransGlobe deck, 簡報, 文字稿／講稿做成簡報, chart or restyle, even when they only paste text and ask to 做成簡報 in a TransGlobe context. Exclude design-system maintenance, generic blue styling, and non-TransGlobe deck outlines or image-prompt decks.
metadata:
  compatibility: PPTX assembly requires Node.js 18 or later and npm (run npm ci once in scripts/); the SVG chart renderer alone needs only Node.js. LibreOffice or PowerPoint for Mac is optional for page previews.
---

# iysl-transglobe

把文字稿做成全球藍簡報，或把既有檔案套用全球藍。成品的標準是原型簡報
[`assets/example-deck.json`](assets/example-deck.json)：每頁一個判斷、每頁有主視覺、
數字看得到出處、圖表在 PowerPoint 裡可以編輯。

## 原則

原型的製作指南只有四句，遇到取捨時回到這四句：

1. **觀點在前，證據在後。** 先給結論頁（主管摘要），再放支撐的數字與圖。
2. **一頁，一個清楚的判斷。** 標題寫結論（「個險是唯一衰退的通路」），不寫主題（「通路表現」）；主題放 eyebrow。
3. **先寫結論，再選最能支持它的圖。** 圖的工作是讓讀者一眼看到標題說的事。
4. **刪減內容優先於縮小字級。** 放不下就拆頁、改成表格或移到講者備忘稿。

數字是簡報的信用，守住三件事：

- 數字來自使用者給的內容，保留原本的精度；沒給的標「未提供」。零是觀察值，缺值才留白。
- 讀者看得到每個數字的單位、期間與來源，比例也看得到分母（lede、圖或頁尾都行）。
- 標題和圖型都只說資料撐得住的事。稿子本身的主張照原意寫；圖型暗示的結構（同一批對象、可加總、真實分布）要資料真的有。

頁數、頁序、版型、選圖、文字密度與講法都由你判斷，以最能說服這群聽眾為準。
下面的骨架、版型和圖型是工具箱，不是清單。

## 文字稿 → 簡報

1. **寫故事線。** 讀完整份稿子，寫下聽眾要帶走的一句話，再列出每頁的一句判斷。
   常見骨架：決策型是封面 → 主管摘要 → 證據（KPI、圖、表）→ 診斷或選項 → 決議事項；
   說明型是封面 → 重點摘要 → 重點拆解 → 流程或時程 → 下一步。稿子有更有力的說法時照它的邏輯走。
2. **每頁配一個主視覺。** 從下方版型挑最能讓讀者一眼看到判斷的那一個。
   只有條列文字的內容是講者稿，放進 `speakerNotes`。
3. **寫 `deck.json`。** 欄位見[版型說明](references/page-layouts.md)，密度照
   [`assets/example-deck.json`](assets/example-deck.json)；圖表見[選圖指南](references/chart-selection.md)
   與[圖表輸入](references/chart-inputs.md)。
4. **建置。** `$SKILL_DIR` 是本 skill 的目錄。

   ```sh
   npm ci --prefix "$SKILL_DIR/scripts"        # 第一次使用時安裝
   node "$SKILL_DIR/scripts/build-deck.js" deck.json deck.pptx
   ```

   `WARN` 是版面提醒（標題太長、文字可能溢出、表格太長、圖太擠）；精簡、拆頁或保留由你決定。
   只有缺必要欄位或資料形狀不對、畫不出來時才會中止。
5. **檢視並改進。** 轉成逐頁圖片，像台下的聽眾一樣看：

   ```sh
   node "$SKILL_DIR/scripts/preview-deck.js" deck.pptx preview
   ```

   判斷是否一眼可見、圖是否在替標題作證、整份是否一路推向結論？找出最弱的一兩頁，
   改到滿意再交付。腳本優先用 LibreOffice（替代字型，只能看版面），沒有時用 Mac 上的 PowerPoint（實際畫面）；
   兩者都沒有時交付時提一句。
6. **交付** PPTX 與 `deck.json`，用幾句話說明故事線，並列出稿子沒有、因此標「未提供」的資料。

## 版型

| `layout` | 用途 |
| --- | --- |
| `cover` | 封面 |
| `summary` | 主管摘要：一個建議加 2–3 個支撐數字；稿子沒有支撐數字時，摘要改用 `flow` 或 `columns` |
| `kpi` | 一個核心數字，加對照（同業、目標、去年）與次要指標 |
| `chart` | 一張圖回答一個問題：高低、變化、組成 |
| `table` | 排名或需要逐項查的精確數值 |
| `compare` | 方案或選項比較，標出建議方案 |
| `list` | 有優先序的原因、風險或行動 |
| `columns` | 並列重點，可帶數字 |
| `process` | 流程、時程、上線步驟 |
| `flow` | 因果或「問題 → 回應」 |
| `decisions` | 深色結尾頁：要聽眾決定或核准的事；聽眾不用做決定時，用 `list` 或 `columns` 收尾 |
| `chapter` | 長簡報的深色章節頁 |

## 圖表

- `ranking`、`ordered`、`trend`、`tracking`、`grouped`、`stacked`、`sharetrend`、`combo`
  產生 PowerPoint 原生圖表，可在 PowerPoint 裡「編輯資料」；其餘圖型嵌入 SVG 並附 PNG 後備。
  需要保留 SVG 時，在該頁加 `"svg": true`。
- 單獨需要 SVG（HTML、Word、純圖）時：`node "$SKILL_DIR/scripts/render-chart.js" input.json chart.svg`。

## 套用到既有檔案

使用者要改的是既有的 PowerPoint、Word、Excel 或 HTML 時，在副本上改，保留原檔；
讀[格式說明](references/formats-and-validation.md)中對應格式的段落。圖表從原生圖表、
內嵌工作簿或來源表格取得數據重畫；只有點陣圖時保留原圖，並列出重畫需要的資料。
簡報若需要重寫才能有清楚的判斷，先說明，再把原檔內容當文字稿走上面的流程重建。

色彩、字型與尺寸見[設計規範](references/design-rules.md)。
