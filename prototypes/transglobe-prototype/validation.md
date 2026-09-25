# 原型驗證紀錄

2026-09-24 的歷史驗證紀錄。當時視覺方向待接受；決策票 [#17](https://github.com/isaac-ys-lin/iysl-skills/issues/17) 已於同日關閉。以下保留該階段的驗證範圍。

## 自動與結構檢查

- `python3 build_demo.py`：前後標籤、120／88／54／38、比例尺、合計 300 通過。SVG 不含 image、script 或 foreignObject。
- `python3 check_office_samples.py`：三種格式各含兩張 SVG 及關聯，圖框皆維持 960:420；Word 的標題、期間、兩段正文、兩張表與分頁保留；Excel 合計公式保留。結果見 `office-checks.json`。
- PowerPoint 完成套件完整性、字體與幾何檢查，以及 Artifact Tool 重匯入；見 `pptx-validation.json`。這些檢查不取代原生畫面檢查。
- Excel 由 Artifact Tool 重算，Data!A1:B6 回讀四項原始數值及合計 300。

## 實際呈現

| 容器 | 實際檢查與結果 |
| --- | --- |
| HTML／SVG | Codex in-app browser 查看簡報、文件、獨立圖表的前後對照，放大與切換正常；缺資料案例保留原始 PNG 並清楚標示未重建。 |
| 窄螢幕 HTML | 390 px viewport（可用寬 375 px）文件無整頁橫向溢出。圖表保留最小可讀尺寸並在容器內捲動，不把全部文字壓縮到手機寬。已恢復預設 viewport。 |
| PowerPoint for Mac | 實際開啟兩頁；原生標題、期間、來源與數據文字可辨識。最後調整至標題 36、期間 24、來源 16 px，圖表等比例，無明顯截字或重疊。 |
| Word for Mac | 實際開啟兩頁，標題、正文、表頭、數值、來源及兩張圖皆呈現；標題採 Cambria／PMingLiU，內文維持 Microsoft JhengHei。 |
| Excel for Mac | Visual 工作表的前後 SVG、原生標題、期間與來源正常；原生字型欄顯示 Microsoft JhengHei。Data 回讀 120／88／54／38，B6 公式列為 `=SUM(B2:B5)`、顯示結果 300。 |

三種 Office 檔案均未出現修復提示。上述為目前安裝的 Mac 版檢查，不代表其他版本、平台或列印引擎已驗證。

## 原型暴露並修正的問題

1. SVG 圖框不符合原比例，導致中文字被拉窄；圖框改為與來源相同長寬比。
2. Word 的圖片替換範圍過大，刪除原生正文；縮小替換範圍並加入文字完整性檢查。
3. Word 白色表頭未搭配底色，畫面不可見；改為閱讀主色。
4. Excel 使用錯誤的字型欄位，落到預設字型；使用已文件化的 `font.name`，並回讀實際顯示字型。

以上支持把「來源資料／文字保真」、「檔案結構」及「實際渲染」分開驗收；封包內存在文字或 SVG，不足以宣稱畫面正確。

## 校準範圍與限制

本例是單期四通路 Focus 比較，未驗證 Ordered、Categorical、密集多頁內容、Windows、Office Web、舊 Office、PDF／列印輸出。SVG 保留文字節點，仍有跨機字型替代風險。PowerPoint 與 Excel 含相容用 PNG 部件，Word 此原型直接嵌 SVG；不宣稱所有 Office 版本皆以向量顯示。

SVG 可由 `data.json` 和生成來源重製，但不提供 Office 原生圖表的「編輯資料」。Excel Data 數值可編輯、合計會重算；修改儲存格不會自動重繪 SVG，需同步原始資料後重製。

待使用者校準：結論式標題、Focus 色彩與閱讀密度，能否作為第一版設計套用 skill 的驗收基準。
