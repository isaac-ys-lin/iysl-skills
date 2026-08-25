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
