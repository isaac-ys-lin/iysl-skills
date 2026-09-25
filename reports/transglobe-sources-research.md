# 全球藍規範來源與可沿用資源

研究票：[確認全球藍規範來源、版本差異與可沿用資源](https://github.com/isaac-ys-lin/iysl-skills/issues/15)  
日期：2026-09-24

歷史來源研究；文末「第一版」建議記錄當時範圍。現行功能與規則見 [iysl-transglobe](../skills/iysl-transglobe/SKILL.md)。

## 結論

新 skill 可以把全球藍做為「來源支持的應用規範」來套用；不應把它表述為完整或已核准的 CIS。使用者指定的公開網站是行為與內容的優先來源；本機資料夾提供可攜 tokens、素材與可重用檢查，但目前是另一個版本快照。

## 最小來源優先序

1. 公開網站 [全球藍設計系統 v2.5.1](https://transglobe-blue.isaacyslin.chatgpt.site/)：本次指定的優先版本。網站可見 54 個範例，涵蓋圖表、簡報與品牌規則，並提供三個 Logo 與 Office 容器下載。
2. 本機 visuals repo：`designs/transglobe-blue-token-system/design-tokens.json`（v2.5.0）；可機讀的顏色、字體角色、字級、間距、版面與圖表規則來源。不得自行視為與 v2.5.1 相同。
3. 同一 repo 的 `designs/transglobe-blue-token-system/COLOR-REFERENCE.md` 與 `CHART-READABILITY.md`：前者定義色彩來源與官方性邊界，後者將圖表規則限制在閱讀任務和容器脈絡。

## 可直接沿用

- 色彩角色與藍階、灰階、Focus／Ordered／Categorical 圖表選色，以及狀態色必須同時呈現符號與文字。
- 角色排印：封面／章節用 Cambria + PMingLiU；內文、圖表與數字用 Arial + Microsoft JhengHei；Mac 後備為 Songti TC／PingFang TC。這是 HTML 規則。
- 三個確認官方的 SVG：`TGL Logo_blue.svg`、`TGL Logo_white.svg`、`TGL Logo_English.svg`。
- `dist/TGL.thmx`、`dist/TGL.potx` 可作可選 Office 起點；`check-share.js` 包含本機分享包的五項下載資產位元組一致性檢查。本次未重跑，不能據此證明線上 v2.5.1 與本機等同。

## 必須保留的界線

- `design-tokens.json` 的狀態是「未核准提案；僅三個 Logo SVG 為確認官方」。非 Logo 的色彩、狀態與版型不得稱為官方 CIS。
- Office 容器只同步配色與白底封面，保留既有 11 個版型及 Noto 字型；它不是 25 頁 HTML 簡報的轉檔，也不是 HTML 字體規則的權威。
- `CHART-READABILITY.md` 的純圖、完整投影片與 HTML 長報告是不同容器；完整簡報的字級下限、16:9 格線和 5% 邊界不可機械套到文件或純圖。
- 現有 `build.js --check`、`check-mac.js`、`lint.js`、`verify-colour.js`、`check-motion.js`、`check-share.js` 與 Office 色彩檢查，是本機 HTML／既有 Office 容器的驗證，不構成 DOCX/XLSX 通用驗收器。

## 建議給後續 skill 的邊界

第一版只要求：讀取上述規範、先依讀者問題選圖表色彩模式、保留資料與原意、採用角色排印與合適 Logo、再按實際輸出格式做最小可見性檢查。後續票再決定各格式的可編輯性策略與人工視覺驗收；不需重建 token 或自動圖表庫。
