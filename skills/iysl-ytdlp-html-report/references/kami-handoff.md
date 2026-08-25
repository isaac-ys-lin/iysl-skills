# Kami 交接契約

Kami 是主線 presentation backend。交給它的只有**已通過 `validate_report_v2.mjs`
的 spec** 加這份契約——不給語意骨架 HTML，也不在事後對它的產物注入錨點。Kami 的
價值在版面結構本身（封面、章節配置、閱讀節奏），把它降級成樣式層就沒有理由選它。

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
第一個 `data-report-section` 之前。Brief 不是第五章，不要給它章節標題。

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
| `narrative`、`process`、`comparison`、`control-gap` | `recap` |
| `key-points` | `key-points` |
| `food-for-thought` | `food-for-thought` |
| `actions` | `actions` |

每個 block 的 `title` 必須逐字出現在**它該在的那一章之內**。放到別章即使文字還在文件裡
也會被擋下——因為 Markdown 版是照真正的對應渲染的，錯置會讓兩份交付物講不同的故事。

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
- reader-facing 禁止文字（字幕來源、轉錄品質、未檢視畫面、`驗證與限制` 等）一律不得
  出現，它們屬於 verification sidecar。這一條是掃**原始碼**，不只是讀者看得到的文字：
  class 名稱、`id`、註解裡出現 `evidence_refs`、`presentation_backend` 這些字一樣會被擋。
- 讀者內容不得出現絕對本機路徑、`file://` 或 Windows 磁碟機路徑。

## 這份契約擋得住什麼、擋不住什麼

這是**結構檢查，不是語意檢查**。

擋得住：整段憑空生出來的讀者內容。沒有錨點、又沒有 chrome 宣告的區塊會被拒絕，所以
排版器沒辦法安靜地多寫一章。

擋不住：在已宣告區塊**內部**改寫語氣、加形容詞、把一句判斷寫得比證據更強；也擋不住
把整段捏造內容塞進一個宣告成 `toc` 或 `running-head` 的區塊裡。錨點只證明這一段對應到
spec 的哪一塊，不證明字句沒有被潤色，chrome 宣告也只證明「這一段自稱是裝飾」。這個邊界
要靠交接時只給已驗證的 spec、以及不要求 Kami 生成新內容來守；驗證器不會幫忙。

## 失敗時的行為

Kami 沒照這份契約做的時候**硬失敗**，不自動退回內建保底。fallback 只保留給「Kami 不
可用」這一種情況。

自動退回會讓兩種不同的事故長成同一個結果：使用者拿到一份能用的報告，但版型悄悄換了
一種，真正的原因（少輸出一個錨點）被吞進 sidecar 的一行。硬失敗醜，但它把該修的東西
留在檯面上。
