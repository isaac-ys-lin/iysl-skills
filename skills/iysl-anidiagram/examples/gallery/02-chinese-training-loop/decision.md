# Decision

## Composition

環形配置：五個階段卡片沿封閉的環順時針排列，環中央放循環的代價（「整理、對齊、定義決策的時間——越來越少」），環的閉合處加紅色標註「回到原點，但更糟」。這個來源不是要交代某一天依序發生了什麼，而是要讓讀者一眼看到「怎麼又回到原點，而且還更糟」——環形讓回流與累積感在靜態畫面就成立，中央文字把循環的後果從「隱含」變成「明說」。

三層閱讀：標題「會議越多，資訊越散」承載 claim；五張卡片與環上箭頭承載結構；卡片副標、中央第三行與底部註解承載細節。

## Rejected Alternatives

- 直線 timeline：會把循環誤讀成只發生一次的事件序列，正好違反 F7。
- 分支 flow：會把注意力拉到判斷點，但這個來源沒有分支——每一步必然推向下一步。
- before/after 對照：能展示變差，但會丟失「中間如何一步步把問題放大」的機制。

## Animation Semantics

Relation 是 loop / cycle。依 `references/animation-semantics.md` 的 Loop / cycle 條目，required motion 是「連續循環、無可見起訖斷點：元素沿封閉路徑行進，永遠繞下去」。實作：一個光點（實心加光暈）以 `animateMotion` + `mpath` 沿 `#loop-ring` 封閉路徑等速行進，`repeatCount="indefinite"`、路徑首尾同點，循環無縫；光點行經每個節點時，節點與對應卡片同步亮起（halo opacity 以錯開的 `keyTimes` 脈衝，起訖值相同）。動畫本身就是論證：這件事沒有終點。

避開的反模式：任何「跑完就結束」的線性動線（cycle never finishes）；五個節點同時脈衝（會失去「現在循環走到哪」的敘事）。

## Coverage

| Fact | 標記 | 圖上落點 |
| --- | --- | --- |
| F1 資訊沒先整理成可判斷內容 | must-keep | 頂部卡片「資訊沒有先整理」＋副標「需求、風險、決策未成為可判斷的內容」 |
| F2 主管不安、加開會議 | must-keep | 右上卡片「主管不安，加開會議」＋副標 |
| F3 資訊散落口頭與零碎訊息 | must-keep | 右下卡片「資訊更散」＋副標「決策散落在口頭對話與零碎訊息裡」 |
| F4 返工增加 | must-keep | 左下卡片「返工增加」＋副標「回頭撈決策、補紀錄、重新確認」 |
| F5 下次更早開會、循環強化 | must-keep | 左上卡片「下次更早開會」＋副標「循環被強化，一圈比一圈嚴重」＋閉合處標註「回到原點，但更糟」 |
| F6 整理對齊時間越來越少 | must-keep | 環中央三行：「整理、對齊、定義決策的時間／越來越少／時間改流向開會、撈訊息、補紀錄」 |
| F7 會反覆加劇的循環，不是一次性列表 | must-keep | 封閉環本身＋無縫循環動畫＋底部註解「這不是一次性的事件序列……」 |

無捨棄項。

## Validation

```bash
python3 skills/iysl-anidiagram/scripts/render_svg.py \
  --svg skills/iysl-anidiagram/examples/gallery/02-chinese-training-loop/diagram.svg \
  --outdir /tmp/anidiagram-02 --basename diagram --check
```

Exit 0（結構驗證、文字碰撞、邊界、motion_nonzero、MP4/PNG 契約全過）。另以肉眼確認 poster PNG（`data-poster-t="4"`，光點停在「資訊更散」節點）在無動畫時即可讀出循環方向與升級邏輯。
