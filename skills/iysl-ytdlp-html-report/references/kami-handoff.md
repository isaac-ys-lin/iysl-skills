# Kami 交接契約

Kami 是主線 presentation backend。交給它的只有**已通過 `validate_report.mjs`
的 spec** 加這份契約——不給語意骨架 HTML，也不在事後對它的產物注入錨點。Kami 的
價值在版面結構本身（封面、章節配置、閱讀節奏），把它降級成樣式層就沒有理由選它。

**排版在隔離的 context 裡進行。** 執行排版的 subagent 只拿得到 spec 和這份契約，
拿不到 clean transcript、metadata 或 source manifest，也不會有人把它們的內容貼進
prompt。這不是禮貌性的規定，而是這份契約的地基：排版器沒看過逐字稿，就沒有素材
可以加料。

它回傳的那一份最終 HTML，就是被驗證、也是交付給讀者的那一份。

## Kami 必須在最終 HTML 上輸出的東西

**四章錨點。** 四個 reader-facing 章節各自要有一個 `data-report-section` 屬性，值
固定為下列四個，且在文件中依序出現：

| 錨點值 | 章節 |
| --- | --- |
| `recap` | 內容重述 |
| `key-points` | 洞見 |
| `food-for-thought` | food for thoughts |
| `actions` | 可行啟發 |

**Brief 錨點。** 掃讀層所在的區塊要帶 `data-report-brief`，恰好一個，且必須出現在
第一個 `data-report-section` 之前。Brief 不是第五章，不要給它章節標題。v2.4 的
`source_limitation.notice` 與「回到原影片」連結也放在這個錨點內，不能省略或改寫。

**Chrome 宣告。** 沒有 spec 來源的排版元素要明確宣告 `data-report-chrome`，值只能是
`cover`、`toc`、`running-head` 其中之一。列舉以外的值一樣會被擋下——宣告本身不是
通行證，它是「我承認這一段沒有證據」的簽名。

## 寫法上的硬規定

- 屬性值用**雙引號或單引號都可以**，但必須有引號，而且必須是真的屬性——寫在
  HTML 註解裡、或藏在別的屬性值裡（例如 `title="data-report-chrome=cover"`）
  都不算數。驗證器解析屬性，不是搜尋字串。
- 宣告可以掛在**任何元素**上，不限 `<section>`。`<div data-report-chrome="toc">`
  一樣有效。
- `id` 在整份文件裡不能重複。四章的 `id` 建議與錨點值分開命名，因為錨點值和
  block id 取自同一套詞彙，直接共用會撞名。

## 文件外殼

最終 HTML 必須是一份完整文件：有 `<html>` 與 `</html>`，而且**內容要包在 `<main>` 裡**。
片段（只有 body 內容）會被擋下。

**不得內嵌 `<script>`**，一個都不行。主題切換、目錄捲動這類互動要放棄，或改用純 CSS。

## 章節歸屬

哪一種 block 屬於哪一章，是語意契約，不是排版判斷。排版器不能改：

| block type | 必須放在哪一章 |
| --- | --- |
| `narrative`、`process`、`comparison`、`control-gap`、`spotlight` | `recap` |
| `key-points` | `key-points` |
| `food-for-thought` | `food-for-thought` |
| `actions` | `actions` |

每個 block 的 `title` 必須逐字出現在**它該在的那一章之內**。放到別章即使文字還在文件裡
也會被擋下——因為 Markdown 版是照真正的對應渲染的，錯置會讓兩份交付物講不同的故事。

每個 block 的最外層元素還必須同時帶 `data-report-block="<block.id>"` 與
`data-report-block-type="<block.type>"`。block 的 title、summary 與所有 item 文字都必須在
這個元素裡；validator 會逐 block 檢查，不能只把文字散落在同一章裡。

## 版面契約

驗證器只管語意骨架，不管好不好看。但同一份 spec 每次出稿應該長得像同一個產品，
所以下面這幾件事**固定**，其餘（網格、留白、色彩深淺、圖表樣式、頁首頁尾內容）
由 Kami 自由決定。

**固定的六件事**

1. **封面**必須存在，帶標題、subtitle、來源、影片長度與 `reading_minutes`。
2. **brief 緊接封面**，在四章之前，視覺上明顯是一個獨立的引言區塊——不是第一章的
   開頭，也不是副標。它是全文唯一可以掃三秒就走的區塊。
3. **四章之間必須有明確的分隔**（換頁、整段留白或分隔線擇一，全文一致）。四章的
   視覺權重相同，不得把其中一章做成附錄樣式。
4. **block 的 `title` 是第二層閱讀**：它必須在掃視時就讀得到，字級與權重明顯高於
   內文、低於章節標題。不要把它縮成內文的粗體第一句。
5. **表格保持表格**。`comparison` 與 `control-gap` 的欄列關係就是它的內容，改寫成
   卡片或條列會把「同一維度可比較」這件事弄丟。
6. **引述**（`transcript_quote` 呈現）全文一種樣式，不要一段一個花樣。

`spotlight` 是內容重述中的編輯插頁。它要比 narrative 醒目，但不能升格成第五章，也不能
拆離 `recap`；保留 block title、item heading 與 text，並用一致的 callout 語法呈現。

`semantic_inventory`、`interpretations`、`completeness_review` 與 `topic_coverage` 是
coordinator 的 completeness contract，不是讀者內容。不要呈現 unit/topic title、sweep、
routing rationale、basis IDs、salience signals、block IDs 或 coverage 摘要。真正可排版的
語意仍是 brief、`source_limitation.notice` 與 blocks。

**基調**

安靜的編輯感：清楚的字級層級、充足留白、克制的一個強調色只用來標記語意狀態。密度
要撐得起細讀，但不能變成雜訊。中文內容用中文字體排版，專有名詞保留原文。

**不要做的**

- 不要為了填滿版面而加裝飾性圖形或圖示。
- 不要把 `narrative` 段落切成卡片；它是連續敘事。
- 不要加互動（目錄捲動、主題切換）——契約禁止 `<script>`。

## 驗證器怎麼看這份 HTML

- **章節標題完全自由。** 章節識別看的是錨點，不是標題文字，也不是標題層級。要用
  `<h1>` 當章、`<h2>` 當小節、要不要目錄與封面，都由 Kami 決定。但 block 自己的
  `title` 不自由：它必須逐字出現。
- **`<body>` 裡的每一段文字都必須落在某個已宣告的區塊之內。** 沒有被涵蓋的文字
  一律違規，不管它包在 `<p>`、`<div>`、`<table>` 還是完全裸露。已宣告區塊裡面的
  子孫由那個區塊負責，不必逐層再宣告。
- 沒有被涵蓋的 sectioning 元素（`section`、`article`、`nav`、`aside`、`header`、
  `footer`）即使暫時沒有文字，也必須帶錨點或 chrome 宣告。
- 一個區塊不能同時宣告錨點與 chrome：要嘛回指 spec，要嘛承認自己沒有證據。
- spec 裡的每一段內容都必須出現在 HTML；brief 的 claim 與每個 takeaway 也一樣。
- `reading_minutes` 由 spec 帶來，直接呈現即可，不要自己重算或省略。
- 除 spec 內固定的 `source_limitation.notice` 外，reader-facing 禁止文字（字幕來源、ASR、
  轉錄品質、`驗證與限制` 等）一律不得出現，它們屬於 verification sidecar。這一條是掃
  **原始碼**，不只是讀者看得到的文字：
  class 名稱、`id`、註解裡出現 `evidence_refs`、`presentation_backend` 這些字一樣會被擋。
- 讀者內容不得出現絕對本機路徑、`file://` 或 Windows 磁碟機路徑。

## 這份契約擋得住什麼、擋不住什麼

這是**結構檢查，不是語意檢查**。

擋得住：整段憑空生出來的讀者內容。沒有錨點、又沒有 chrome 宣告的區塊會被拒絕，所以
排版器沒辦法安靜地多寫一章。

擋不住：在已宣告區塊**內部**改寫語氣、加形容詞、把一句判斷寫得比證據更強；也擋不住
把整段捏造內容塞進一個宣告成 `toc` 或 `running-head` 的區塊裡。錨點只證明這一段對應到
spec 的哪一塊，不證明字句沒有被潤色，chrome 宣告也只證明「這一段自稱是裝飾」。

剩下的風險因此收斂成一種：排版器只能拿 spec 裡已經有的東西去潤色或改寫，不可能引入
逐字稿裡的新事實——它沒看過。這一段是 context 隔離守住的，不是驗證器守住的；把逐字稿
遞給排版器，這條保證就消失了。

## 失敗時的行為

Kami 沒照這份契約做的時候**硬失敗**，不自動退回內建保底。fallback 只保留給「Kami 不
可用」這一種情況。

自動退回會讓兩種不同的事故長成同一個結果：使用者拿到一份能用的報告，但版型悄悄換了
一種，真正的原因（少輸出一個錨點）被吞進 sidecar 的一行。硬失敗醜，但它把該修的東西
留在檯面上。
