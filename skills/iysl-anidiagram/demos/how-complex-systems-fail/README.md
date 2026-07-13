# 複雜系統如何失敗

根據 Richard I. Cook 的〈[How Complex Systems Fail](https://how.complexsystems.fail/)〉
製作的動畫解說圖。

## 核心主張

複雜系統不是靠消滅所有故障而安全。它平時就在危險且劣化的狀態中運作，
多層防禦與人員調適則持續阻擋事故軌跡。

## 視覺與動畫理由

- **關係：** 系統圖。
- **視覺：** 深色事故作業場，以琥珀色表示風險、酸綠色表示人員介入，
  搭配等寬技術字體與儀表刻線。
- **空間：** 滿版、偏心的斜向運作走廊。
- **動畫：** 第一條軌跡先被偏轉與攔截；兩個防禦缺口再短暫對齊，
  只有對齊完成後，另一個罕見的失敗機會才會逼近事故邊界。

靜態海報已包含所有 must-keep 事實；動畫只負責解釋因果變化，
不承載靜態圖中缺少的資訊。

## 檔案

- `diagram.svg` — 可編輯、自包含的 SMIL 原始檔。
- `how-complex-systems-fail.mp4` — H.264 影片，9 秒無縫循環。
- `how-complex-systems-fail.png` — 資訊完整的靜態海報。
- `final-render-report.json` — 從最終路徑執行 renderer 的驗證證據。

## 驗證或重現

從本目錄執行：

```bash
python3 ../../scripts/render_svg.py \
  --svg diagram.svg \
  --outdir . \
  --basename how-complex-systems-fail \
  --check
```

勝出案經過兩輪修正，已通過事實覆蓋、動畫語義、三層閱讀、視覺品質、
來源忠實度與跨候選多樣性審查。
