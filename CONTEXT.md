# Reusable Codex Skills

This context defines the product language used to design and maintain the reusable Codex skills in this repository.

## Language

**Visual explainer**:
A skill experience that helps an adult novice understand one primary concept through a visual and a concise plain-language explanation.
_Avoid_: ELI5, HTML explainer, general explanation

**Primary concept**:
The single central idea that a visual explainer organizes around, even when the source includes several related ideas.
_Avoid_: Topic list, exhaustive summary

**Brief**:
影片閱讀報告最前面的掃讀層：一句判斷加三到四個帶走重點，每一項都回指逐字稿證據。它不參與四章的認知流。
_Avoid_: 執行摘要, summary, TL;DR, 導言

**Recap**:
四章的第一章「內容重述」，重建影片主線、例子與轉折的完整敘事層。
_Avoid_: summary, 摘要, 內容摘要

**Section anchor**:
標在最終 HTML 上、讓驗證器辨認語意章節的結構化屬性，與標題層級無關。
_Avoid_: 標題文字比對, h2 掃描

**Report chrome**:
最終 HTML 中沒有 spec 來源的排版元素，例如封面、目錄與頁首頁尾；必須明確宣告，否則視為未經證據治理的讀者內容。
_Avoid_: 裝飾元素, 版型元件

**Presentation backend**:
產出最終受驗 HTML 的排版器。Kami 是主線，內建 v2 模板只在 Kami 不可用時作為離線保底。
_Avoid_: 渲染器, 模板引擎

**Semantic inventory**:
從乾淨逐字稿抽出的內部完整清單；逐項保存語意不同的主張、背景、例子、數據、決策、取捨、限制、問題與軼事，並先於任何呈現方式建立。它不是讀者面向的摘要。
_Avoid_: 主題摘要, 大綱, 精華

**Semantic unit**:
Semantic inventory 中最小且可獨立驗證的內容單位。只有刪除或反轉一段內容會改變結論、行動或證據時才拆成不同 unit；重複表述維持同一 unit，但可連到多段證據。
_Avoid_: 句子, 段落, transcript chunk

**Disposition**:
Semantic unit 的明確處置結果，只能是 `included`、`compressed_duplicate` 或 `excluded_nonsemantic`。有效語意不得因篇幅或閱讀時間而被排除。
_Avoid_: 重要性評分, 任意刪節, 編輯偏好

**Cognitive job**:
一個 semantic unit 在讀者理解流程中負責的工作。第一版封閉為 `explain`、`sequence`、`compare`、`control`、`emphasize`、`derive_insight`、`raise_question`、`prompt_action`，再由 representation router 映射到既有 block types。
_Avoid_: block type, 版面元件, 視覺風格

**Interpretation**:
報告作者從一個或多個 semantic units 推導出的洞察、問題或行動建議。它必須列出 `basis_unit_ids`，且不可偽裝成影片直接陳述的內容。
_Avoid_: semantic unit, 原片主張, 無來源評論

**Completeness review**:
在 schema 驗證之外，依逐字稿順序抽取、開頭中段結尾反向掃描，以及 transcript span 覆蓋情形，判斷有效語意是否都有明確去向的審查。
_Avoid_: schema validation, 重點檢查, 字數檢查

**Source limitation**:
正式報告對證據邊界的讀者面向聲明。影片報告只承諾乾淨逐字稿內的語意完整，並明示純畫面資訊可能未被涵蓋；讀者需要核對畫面、語氣或示範時，應回到原影片。
_Avoid_: 驗證失敗, visual audit, 免責聲明

**Representation router**:
替每個 semantic unit 指派認知任務，選擇足以承載內容的最小既有報告區塊，並記錄選擇理由的內部決策層。
_Avoid_: renderer, presentation backend, layout engine

**Exploration view**:
僅在使用者明確要求時，從已驗證且適合讀者閱讀的報告內容建立的對話內視覺化。它不屬於標準產物、不取代正式報告，也不回寫 spec。
_Avoid_: presentation backend, 第二份最終 HTML, report artifact
