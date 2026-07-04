# Decision

## Source Type

繁體中文能力說明稿，用來教學智慧代理工作流的分層能力模型。

## Primary Claim

智慧代理工作流的可交付成果來自多層能力堆疊；上層品質建立在下層能力穩定存在的前提上。

## Relation

分層與依賴關係，不是事件順序。

## Layout

`stack`

## Why This Fits

這個案例的重點是「哪一層支撐哪一層」，而不是流程從左走到右。堆疊能自然表達基礎能力、代理工作流能力、治理能力到最終成果之間的向上承接，也方便用簡短中文標籤維持高可讀性。

## Rejected Alternatives

`flow` 會讓人誤以為能力是執行時一關一關跑過去。`timeline` 會暗示部署或學習歷程。`architecture` 雖然能裝更多元件，但對這種教學心智模型來說太重，會稀釋層次感。

## Style And Animation

視覺上要穩、乾淨、少裝飾，讓層與層之間的支撐感最明確。動畫適合做由下往上的建立感，提醒讀者「沒有底層，就沒有上層」，但靜態圖本身也要先成立。

## Validation

確認 brief 與分層判讀一致。`spec.json` 應驗證每層標籤長度、層距與中文字體可讀性，並以 `--verify --check` 通過 renderer 檢查。
