# 報告結構

這份 reference 規範要轉成 HTML 的分析 Markdown。Report 是給讀者看的，不是給 operator 查錯的執行紀錄。

## 目錄

- 讀者、語氣與跨語言原則
- Watch-equivalent 內容分流
- 內容輸出與去 AI 味
- v2 structured report contract
- 通用品質、交付自檢與禁止內容

## 讀者假設

預設讀者是有工作經驗、對影片主題有基礎理解但沒看過這支影片的人。不需要解釋領域常識，但要把影片特有的觀點、邏輯和例子交代清楚，讓讀者讀完後能判斷「這支影片值不值得看」和「有什麼可以用」。

## Watch-equivalent 內容分流

目標不是縮短逐字稿，而是讓讀者用更少時間取得接近看完影片的理解：

- 語音承載的主張、例子與轉折，用重述、key points 或比較文字呈現。
- 逐字稿明確描述的流程、共同維度比較、控制與缺口，才重畫成 explanatory visuals。
- 看完內容後仍值得追問的矛盾與取捨，放進 food for thoughts。
- 不下載影片、不擷取畫面。視覺化只編碼逐字稿中的關係與數值；縮圖只作來源錨點。

不要為了「看起來像完整影片報告」硬加視覺。沒有結構性關係時，清楚的文字比裝飾圖更接近觀看等價。

## 語氣

像一篇給同事看的深度整理，不是學術論文也不是社群貼文。用直接的陳述句，避免：

- 過度客氣的敬語（「不禁讓我們思考」）
- 行銷式語氣（「絕對不能錯過」）
- AI 八股句型（「總結來說」「值得注意的是」「這表明了一個重要趨勢」）
- 不必要的後設描述（「以下將分析」「本報告整理了」）
- 只在段末補一句抽象總結（「這說明⋯⋯」「可以看出⋯⋯」）
- 把具體觀察硬升華成普遍道理
- 過度工整的對比句式（「不是 A，而是 B」「真正重要的不是 X，而是 Y」）
- 連續使用同格式粗體小標，讓每個 bullet 都像模板生成

## 跨語言原則

英文逐字稿整理成繁中報告時：

- 專有名詞保留英文（不硬翻），概念性用語用中文表達，首次出現時括號附英文。
- 引用講者原話時，可用英文原文加中文意譯。
- 不要逐句翻譯逐字稿；內容重述的目標是讓中文讀者理解內容，不是翻譯練習。

## 內容輸出重點

這個 skill 的主要價值不是「把影片塞進固定模板」，而是讓讀者讀完後真的比較懂這支影片。寫作時優先處理三件事：

1. 讓讀者先知道影片的主線，而不是先丟結論。
2. 把講者的判斷、例子和轉折保留下來，不要壓成泛用摘要。
3. 把可以討論的張力寫出來，不要把每個問題都收成漂亮但空泛的結論。

段落可以有節奏，不必每段都一樣長。重要段落可以多寫兩三句，把例子講清楚；低價值的場面話直接刪掉。

## 去 AI 味規則

交付前檢查全文，優先刪掉這些句型：

- 段落最後一句只是在重複前文。
- 把具體工程、產品、研究觀察升華成普世道理。
- 用「值得注意的是」「這表明」「由此可見」起手，但後面沒有新資訊。
- 用「首先、其次、最後」排隊，讓文章像制式講稿。
- 用「講者提到」「影片指出」開頭太多次，導致每一點都像摘要。
- 為了顯得完整，補進逐字稿沒有支撐的推論。

保留有質地的句子：具體例子、講者用詞、矛盾、猶豫、前後轉折、和讀者能拿去判斷的條件。

## v2 structured report contract

以 `report-v2.schema.json` 建立 structured JSON spec，先驗證再從同一 spec 渲染 Markdown 與 desktop HTML。

報告是兩層閱讀。上層是 `brief`：一句 claim 回答「這支影片在吵什麼、值不值得往下讀」，加三到四個可單獨引用的 takeaways。claim 的 claim type 只能是 `speaker_claim` 或 `report_synthesis`；claim 與每個 takeaway 各自帶 `evidence_refs`，不共用一組，因為 takeaway 是讀者最可能單獨引用的一句。

下層是四個 reader-facing 章節，固定依序為 `內容重述`、`洞見`、`food for thoughts`、`可行啟發`。`brief` 不是第五章：四章是理解 → 分析 → 反思 → 行動的認知流，`brief` 不參與那個流程。

takeaway 允許和 `key-points` 講同一件事，但措辭必須不同：上層是一句話版，下層是帶脈絡版。

### Evidence sufficiency gate

建立 spec 前，先把逐字稿證據映射到 schema 要求的最小內容：一個 `brief`
（claim 加三到四個 takeaways）、至少一個 `內容重述` block、一個 `key-points`
item、一個 `food-for-thought` item，以及一個 `actions` item；每一項都必須有
可回指 clean transcript 的 `evidence_refs`。這是 evidence gate，不使用字數或
片長作代理門檻。

`brief` 撐不起來時同樣停止，不得只產出四章。掃讀層是讀者最先看、也最可能
只看的一層，讓它可選等於讓兩層閱讀可選。

若任何必填項沒有逐字稿證據，停止於 source preparation。保留 source
manifest 與 clean transcript，在最終回覆指出缺少支撐的 section；不要建立
v2 spec、reader-facing Markdown/HTML 或 verification sidecar。只有通過此 gate
的素材才適用下方完整 v2 contract，不得為了通過 schema 硬編問題、洞見或行動。

### Evidence registry

- `evidence[].transcript_quote` 只能摘自 clean transcript；metadata、縮圖、留言或外部知識不可成為語意或視覺證據。
- evidence id 在同一份 spec 內唯一。block 與所有 paragraph/node/row/item 都要用非空 `evidence_refs` 指回 registry。
- 縮圖只作為來源錨點，不能支撐 process、comparison、control-gap、key point 或 action。
- 無法以逐字稿支撐的內容不要放入 spec；需要保留時改寫成有 evidence 的 `open_question`。

### Claim type

- `speaker_claim`：講者在逐字稿中直接表達的主張，不把報告推論冒充成講者原話。
- `report_synthesis`：跨一段或多段 evidence 的報告綜整，措辭要保留推論邊界。
- `open_question`：逐字稿留下的張力或未決問題，不寫成已驗證結論。

### Adaptive blocks 與固定章節

- `內容重述`：至少放入一個 `narrative`、`process`、`comparison` 或 `control-gap`。一般敘事、訪談與沒有結構性視覺關係的影片用 `narrative`；只有逐字稿真的支撐關係時才用視覺 block。
- `洞見`：放入 `key-points`，至少要有一個。
- `food for thoughts`：放入 `food-for-thought`，至少要有一個。
- `可行啟發`：放入 `actions`，至少要有一個。

- `key-points`：通常保留 3–5 個真正影響理解的重點，每點用 heading 先交付判斷，再用 text 保留具體內容。
- `narrative`：用一個以上有各自 evidence refs 的段落重建主線、例子與轉折；它是內容重述的正常文字載體，不是 visual fallback 的失敗狀態。
- `process`：只在逐字稿有至少三個相依步驟，或三個以上順序會改變意義的事件時使用。論證鏈或 timeline 只有符合這個條件才可用 process 重畫。
- `comparison`：只有各方案共享明確共同維度時使用 columns/rows；沒有共同維度就改用 key points。
- `control-gap`：逐列對照 control、observed、gap；三欄都必須能回到同列 evidence。
- `actions`：每個 item 寫具體 action，可用 `when` 限定適用場景。
- `food-for-thought`：保留 1–3 題實質張力；每題不能靠重述影片直接回答，答案應會改變決策、流程或控制設計。context 只補足問題成立的條件，不重複摘要；素材不足以形成有意義問題時，不要硬湊完整報告。

逐字稿若描述選單、點擊與畫面切換，可以用 process 畫成「操作狀態圖」，但只能寫出逐字稿明講的狀態與動作；不可猜測按鈕位置、配色、欄位排列或重建真實介面。

若逐字稿沒有完整、同口徑、可比較的數據，不可 chart。v2 first slice 不支援 chart；不要用定性詞或零散數字偽裝成圖表數據。

### Reader-safe output

- 讀者欄位禁止 `file://`、絕對本機路徑、command、traceback 或 cache/debug ledger。
- `claim_type`、`evidence_refs`、evidence id、證據欄與逐字稿 evidence appendix 全部留在幕後，不進 reader-facing Markdown/HTML。
- 所有字串進 HTML 前必須 escape；template 不使用 inline script、外部 JavaScript 或本機資源。
- 預設 acceptance surface 是 desktop browser；不預設執行 mobile viewport 或 screenshot QA。
- 不顯示字幕/ASR、未檢視畫面、轉錄品質或其他來源限制；全部寫進 verification sidecar。

## 區塊設計邏輯

`內容重述` 回答：「影片講了什麼？主線怎麼展開？」

`洞見` 回答：「從逐字稿可以判斷出哪些觀點，而且為什麼重要？」

`food for thoughts` 回答：「理解內容和分析之後，有哪些值得繼續想的問題和張力？」

`可行啟發` 回答：「讀者明天可以怎麼用？」

## 各區塊品質約束

以下約束針對 v2 spec 的各類 block。這裡的數量是**品質目標**，evidence sufficiency gate 的最小必要是另一回事：gate 決定「素材夠不夠產出報告」，品質目標決定「產得出來的報告好不好」。長度與數量是內容判斷，Markdown 與 HTML 的呈現形式由渲染器決定，不在這裡規範。

### narrative（內容重述）

- 長度約 clean transcript 的 15-25%，依影片密度調整。影片 < 10 分鐘時可以較短，但仍需重建脈絡。
- 重建主線、例子、轉折、比較與結論；可以重排順序，但不能加入逐字稿沒有的新事實。
- 保留講者的關鍵用語、比喻和具體案例，不要抽象化。

❌「講者討論了 AI 的發展趨勢和挑戰。」（空洞，讀者不知道討論了什麼）
✅「講者用印刷術類比 AI 的衝擊，主張瓶頸在分發而非生產——他舉了報紙編輯室的例子⋯⋯」

### key-points（洞見）

- 三到五點真正影響理解的重點。每點用 heading 先交付判斷，再用 text 保留具體內容與「為什麼重要」。
- 需要時用一句關鍵引述或時間標記支撐，不需要每點都引。
- 分析的是「逐字稿透露了什麼判斷和邏輯」，不是「講者說了什麼」。

❌「講者認為 AI 會改變世界。」（複述，不是洞見）
✅「講者把 AI 的衝擊類比成印刷術而非電力，暗示他認為瓶頸在分發而非生產——這和主流『算力即一切』的論述相反，值得注意他的推論前提。」

### food-for-thought

- 一到三題實質張力。每題應該像一個可以想一整天的 prompt。
- 挖矛盾、張力、未回答的問題、隱含的取捨。
- 每題不能靠重述影片直接回答，答案應該會改變決策、流程或控制設計。
- 不是摘要，也不是 key-points 的重複。

❌「這支影片談了 AI 的未來，值得深思。」（太泛，沒有張力）
✅「如果訓練成本降到接近零，品質控制的價值會上升還是消失？」

### actions

- 至少三點。每點需要有具體場景或判斷條件，可用 `when` 限定適用場景。
- 可操作 = 讀者看完知道「在什麼情境下做什麼」。

❌「要持續學習新技術。」（抽象價值觀，不是啟發）
✅「如果你的團隊在評估 LLM 供應商，講者建議先跑一輪 retrieval baseline 再比較——這可以省掉至少一輪不必要的 fine-tuning 實驗。」

## 通用品質標準

- 除非使用者另有要求，使用自然的台灣繁體中文。
- 所有主張都要以 clean transcript 為根據，不要只看標題或 metadata 推論。
- 長影片要掃過開頭、中段、結尾；若有章節或使用者提供的時間戳，也要納入。
- 若逐字稿品質差但仍足以支撐內容，降低 reader-facing 主張強度，並把具體限制寫進 sidecar。
- 若素材太短，不足以產出深度洞見，直接說明，不要硬湊。
- 所有來源限制與完整驗證資訊都放在 sidecar；report 不建立 `驗證與限制` 或同義尾段。

## 交付前品質自檢

交付前自我檢查：

1. `內容重述` 讀完後，是否比只看標題多知道了具體內容？
2. `洞見` 每點拿掉「講者認為」後，是否還有分析價值？
3. `food for thoughts` 每點是否能獨立引發一個有意義的討論？
4. `可行啟發` 每點是否有場景或條件，而不只是抽象建議？
5. 全文是否有 AI 八股句型殘留？

若任一項不通過，修改後再交付。

## 禁止放進 report 的內容

以下內容只能放在 `<video_id>.verification.md` sidecar：

- source URL 和 resolved URL 的完整 ledger
- 字幕／ASR 來源、轉錄品質、可能誤聽、未檢視畫面與上下文不足等限制
- metadata、transcript、audio、cache 的完整本機路徑
- 抽取工具完整命令
- stderr / traceback / debug log
- fetch_results.jsonl 的完整內容
- 完整時間戳 ledger
- operator-only 判斷，例如 DNS retry、backend crash、cache reuse 細節
